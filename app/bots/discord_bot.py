import discord
from discord.ext import commands
from discord.ext import tasks
from discord import app_commands
from app.config.settings import get_settings
import time

# 体验权限申请按钮视图
class TrialView(discord.ui.View):
    def __init__(self, manager, settings):
        super().__init__(timeout=None)  # 永久有效
        self.mgr = manager
        self.settings = settings

    @discord.ui.button(label="申请体验", style=discord.ButtonStyle.primary, emoji="🎮", custom_id="trial_apply")
    async def apply_trial(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = str(interaction.user.id)
        user_name = interaction.user.name
        print(f'[Membership] 🔍 用户 {user_name}({user_id}) 点击申请体验按钮')
        
        ok, msg = self.mgr.can_start_trial(user_id)
        
        if not ok:
            print(f'[Membership] ❌ 用户 {user_name}({user_id}) 申请体验失败: {msg}')
            await interaction.response.send_message(
                f"❌ {msg}\n\n" +
                ("• 每个会员只能获得一次体验机会\n" if "已使用" in msg else "") +
                ("• 您当前已有体验权限，请等待体验时间结束" if "进行中" in msg else ""),
                ephemeral=True
            )
            return
        
        # 开始试用
        print(f'[Membership] 📝 开始为用户 {user_name}({user_id}) 创建体验记录')
        self.mgr.start_trial(user_id)
        
        # 分配会员角色（如果有配置）
        role_assigned = False
        if not isinstance(interaction.user, discord.Member):
            print(f'[Membership] ⚠️ 用户 {user_name}({user_id}) 不是 Member 对象，无法分配角色')
        elif not self.settings.MEMBER_ROLE_ID:
            print(f'[Membership] ⚠️ MEMBER_ROLE_ID 未配置，跳过角色分配')
        else:
            try:
                role_id = int(self.settings.MEMBER_ROLE_ID)
                role = interaction.guild.get_role(role_id)
                if not role:
                    print(f'[Membership] ❌ 角色 ID {role_id} 不存在于服务器中')
                else:
                    # 检查用户是否已有该角色
                    if role in interaction.user.roles:
                        print(f'[Membership] ℹ️ 用户 {user_name}({user_id}) 已有角色 {role.name}')
                        role_assigned = True
                    else:
                        # 检查机器人权限
                        bot_member = interaction.guild.me
                        if not bot_member.guild_permissions.manage_roles:
                            print(f'[Membership] ❌ 机器人没有管理角色权限 (manage_roles)')
                        elif role.position >= bot_member.top_role.position:
                            print(f'[Membership] ❌ 角色 {role.name} 的位置高于或等于机器人的最高角色，无法分配')
                        else:
                            await interaction.user.add_roles(role, reason="体验权限申请")
                            role_assigned = True
                            print(f'[Membership] ✅ 成功为用户 {user_name}({user_id}) 分配角色 {role.name}({role_id})')
                            # 验证角色是否真的被添加
                            await interaction.user.fetch()  # 刷新用户信息
                            if role in interaction.user.roles:
                                print(f'[Membership] ✅ 验证：用户 {user_name} 现在拥有角色 {role.name}')
                            else:
                                print(f'[Membership] ⚠️ 警告：角色分配后验证失败，用户可能没有该角色')
            except ValueError as e:
                print(f'[Membership] ❌ MEMBER_ROLE_ID 格式错误: {e}')
            except discord.Forbidden as e:
                print(f'[Membership] ❌ 分配角色权限不足: {e}')
            except Exception as e:
                print(f'[Membership] ❌ 分配角色失败: {e}')
                import traceback
                traceback.print_exc()
        
        trial_hours = self.settings.TRIAL_DURATION_HOURS
        role_status = "✅ 角色已分配" if role_assigned else "⚠️ 角色未分配（请检查配置）"
        
        await interaction.response.send_message(
            f"✅ 体验权限申请成功！\n\n"
            f"🎉 您已获得 {trial_hours} 小时的体验权限\n"
            f"⏰ 体验时间结束后，权限将自动移除\n\n"
            f"{role_status}",
            ephemeral=True
        )
        print(f'[Membership] ✅ 用户 {user_name}({user_id}) 申请体验权限完成，角色分配: {"成功" if role_assigned else "失败"}')

    @discord.ui.button(label="查询时长", style=discord.ButtonStyle.secondary, emoji="⏱️", custom_id="trial_status")
    async def check_status(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = str(interaction.user.id)
        st = self.mgr.get_status(user_id)
        
        now = int(time.time())
        messages = []
        
        # 体验状态
        if st['trial_end'] and st['trial_end'] > now:
            remaining = st['trial_end'] - now
            hours = remaining // 3600
            minutes = (remaining % 3600) // 60
            messages.append(f"🎮 **体验权限**: 进行中\n⏰ 剩余时间: {hours}小时{minutes}分钟")
        elif st['used_trial']:
            messages.append(f"🎮 **体验权限**: 已使用")
        else:
            messages.append(f"🎮 **体验权限**: 未使用")
        
        # 正式会员状态
        if st['is_member'] and st['member_end']:
            remaining = st['member_end'] - now
            days = remaining // 86400
            hours = (remaining % 86400) // 3600
            messages.append(f"👑 **正式会员**: 是\n⏰ 剩余时间: {days}天{hours}小时")
        else:
            messages.append(f"👑 **正式会员**: 否")
        
        await interaction.response.send_message(
            "\n\n".join(messages),
            ephemeral=True
        )

class MembershipCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        from app.services.membership.manager import MembershipManager
        self.bot = bot
        self.mgr = MembershipManager()
        self.settings = get_settings()

    async def cog_load(self):
        # 注册持久化视图（按钮）- 必须在cog_load中注册
        self.bot.add_view(TrialView(self.mgr, self.settings, self.bot))
        # 启动定期检查任务
        if not self._check_expired.is_running():
            self._check_expired.start()
        print('[Membership] ✅ MembershipCog 已加载')
        if not self.settings.MEMBER_ROLE_ID:
            print('[Membership] ⚠️ 警告: MEMBER_ROLE_ID 未配置，申请体验时不会分配角色')
        else:
            print(f'[Membership] ℹ️ 配置的会员角色 ID: {self.settings.MEMBER_ROLE_ID}')

    async def cog_unload(self):
        # 停止定期检查任务
        if self._check_expired.is_running():
            self._check_expired.cancel()

    @tasks.loop(minutes=5.0)
    async def _check_expired(self):
        """定期检查并移除过期的体验权限和会员角色"""
        if not self.settings.GUILD_ID or not self.settings.MEMBER_ROLE_ID:
            return
        
        try:
            guild = self.bot.get_guild(int(self.settings.GUILD_ID))
            if not guild:
                return
            
            role = guild.get_role(int(self.settings.MEMBER_ROLE_ID))
            if not role:
                return
            
            now = int(time.time())
            removed_count = 0
            
            # 检查所有有该角色的成员
            for member in role.members:
                user_id = str(member.id)
                st = self.mgr.get_status(user_id)
                
                # 检查体验权限是否过期（6小时后自动撤销）
                trial_expired = st.get('trial_end') and st['trial_end'] <= now
                # 检查正式会员是否有效
                is_member_valid = st.get('is_member') and st.get('member_end') and st['member_end'] > now
                
                # 如果体验权限过期，且用户没有有效的正式会员，则移除角色
                if trial_expired and not is_member_valid:
                    try:
                        await member.remove_roles(role, reason="体验权限已过期（6小时）")
                        removed_count += 1
                        remaining_time = st['trial_end'] - now
                        hours_over = abs(remaining_time) // 3600
                        print(f'[Membership] ✅ 已移除用户 {member.name}({user_id}) 的会员角色（体验权限已过期 {hours_over} 小时）')
                    except Exception as e:
                        print(f'[Membership] ⚠️ 移除用户 {member.name}({user_id}) 角色失败: {e}')
                # 如果正式会员也过期，也移除角色
                elif not is_member_valid and st.get('member_end') and st['member_end'] <= now:
                    try:
                        await member.remove_roles(role, reason="正式会员权限已过期")
                        removed_count += 1
                        print(f'[Membership] ✅ 已移除用户 {member.name}({user_id}) 的会员角色（正式会员权限已过期）')
                    except Exception as e:
                        print(f'[Membership] ⚠️ 移除用户 {member.name}({user_id}) 角色失败: {e}')
            
            if removed_count > 0:
                print(f'[Membership] 📊 本次检查移除了 {removed_count} 个过期权限')
        except Exception as e:
            print(f'[Membership] ❌ 检查过期权限异常: {e}')

    @app_commands.command(name="trial_message", description="发送体验权限申请消息（仅管理员）")
    @app_commands.describe(channel="要发送消息的频道（留空则在当前频道发送）")
    async def send_trial_message(self, interaction: discord.Interaction, channel: str = None):
        # 检查管理员权限
        admin_roles = set(self.settings.ADMIN_ROLE_IDS)
        if admin_roles and isinstance(interaction.user, discord.Member):
            user_roles = {str(r.id) for r in interaction.user.roles}
            if not (user_roles & admin_roles):
                await interaction.response.send_message("❌ 无权限，仅管理员可使用此命令", ephemeral=True)
                return
        
        # 处理频道参数
        if channel:
            # 尝试解析频道ID或提及
            try:
                # 如果是频道ID
                channel_id = int(channel.strip('<#>').replace('#', ''))
                target_channel = self.bot.get_channel(channel_id) or interaction.guild.get_channel(channel_id)
            except (ValueError, AttributeError):
                # 如果解析失败，使用当前频道
                target_channel = interaction.channel
        else:
            target_channel = interaction.channel
        
        if not isinstance(target_channel, discord.TextChannel):
            await interaction.response.send_message("❌ 无效的频道，请在文本频道中使用此命令", ephemeral=True)
            return
        
        # 创建消息内容
        trial_hours = self.settings.TRIAL_DURATION_HOURS
        embed = discord.Embed(
            title="🎮 体验权限申请",
            description=(
                "点击下方按钮申请体验权限。\n\n"
                "⚠️ **注意事项：**\n"
                "• 每个会员可以获得一次体验机会\n"
                "• 体验会员可以体验部分频道\n"
                "• 体验时间结束后，权限将自动移除\n"
                "• 点击查询时长按钮可查看剩余会员时间\n\n"
                f"⏰ **体验时长**: {trial_hours}小时"
            ),
            color=discord.Color.blue()
        )
        
        # 先响应交互，避免超时
        try:
            await interaction.response.defer(ephemeral=True)
        except discord.InteractionResponded:
            # 如果已经响应过，使用 followup
            pass
        
        # 创建视图（包含按钮）
        view = TrialView(self.mgr, self.settings, self.bot)
        
        try:
            # 发送消息到目标频道
            await target_channel.send(embed=embed, view=view)
            
            # 使用 followup 发送确认消息
            try:
                await interaction.followup.send(
                    f"✅ 体验权限申请消息已发送到 {target_channel.mention}",
                    ephemeral=True
                )
            except discord.InteractionResponded:
                # 如果已经响应，尝试编辑响应
                await interaction.edit_original_response(
                    content=f"✅ 体验权限申请消息已发送到 {target_channel.mention}"
                )
            
            print(f'[Membership] ✅ 管理员 {interaction.user.name} 在频道 {target_channel.name} 发送了体验权限申请消息')
        except discord.Forbidden as e:
            error_msg = f"❌ 发送失败: 机器人没有在频道 {target_channel.mention} 发送消息的权限"
            try:
                await interaction.followup.send(error_msg, ephemeral=True)
            except:
                await interaction.edit_original_response(content=error_msg)
            print(f'[Membership] ❌ 发送体验权限申请消息失败（权限不足）: {e}')
        except discord.NotFound as e:
            error_msg = f"❌ 发送失败: 频道 {target_channel.mention} 不存在或无法访问"
            try:
                await interaction.followup.send(error_msg, ephemeral=True)
            except:
                await interaction.edit_original_response(content=error_msg)
            print(f'[Membership] ❌ 发送体验权限申请消息失败（频道不存在）: {e}')
        except Exception as e:
            error_msg = f"❌ 发送失败: {str(e)}"
            try:
                await interaction.followup.send(error_msg, ephemeral=True)
            except:
                try:
                    await interaction.edit_original_response(content=error_msg)
                except:
                    pass
            print(f'[Membership] ❌ 发送体验权限申请消息失败: {e}')
            import traceback
            traceback.print_exc()

    @app_commands.command(name="member", description="管理员管理会员资格")
    async def member(self, interaction: discord.Interaction, action: str, user: discord.User, days: int = 0):
        # 简单角色校验
        admin_roles = set(self.settings.ADMIN_ROLE_IDS)
        if admin_roles and isinstance(interaction.user, discord.Member):
            user_roles = {str(r.id) for r in interaction.user.roles}
            if not (user_roles & admin_roles):
                await interaction.response.send_message("无权限", ephemeral=True)
                return
        uid = str(user.id)
        if action == 'add':
            self.mgr.add_member(uid, days or 30)
            # 分配会员角色
            if isinstance(user, discord.Member) and self.settings.MEMBER_ROLE_ID:
                try:
                    role = interaction.guild.get_role(int(self.settings.MEMBER_ROLE_ID))
                    if role:
                        await user.add_roles(role, reason=f"管理员添加会员 {days or 30} 天")
                except Exception as e:
                    print(f"[Membership] ⚠️ 分配角色失败: {e}")
            await interaction.response.send_message(f"✅ 已为 {user.mention} 添加会员 {days or 30} 天")
        elif action == 'remove':
            self.mgr.remove_member(uid)
            # 移除会员角色
            if isinstance(user, discord.Member) and self.settings.MEMBER_ROLE_ID:
                try:
                    role = interaction.guild.get_role(int(self.settings.MEMBER_ROLE_ID))
                    if role and role in user.roles:
                        await user.remove_roles(role, reason="管理员移除会员")
                except Exception as e:
                    print(f"[Membership] ⚠️ 移除角色失败: {e}")
            await interaction.response.send_message(f"✅ 已移除 {user.mention} 的会员资格")
        elif action == 'status':
            st = self.mgr.get_status(uid)
            await interaction.response.send_message(f"试用: {st['trial_status']} | 正式会员: {'是' if st['is_member'] else '否'} | 到期: {st['member_end']}")
        else:
            await interaction.response.send_message("用法: /member [add|remove|status] ...")

class OKXCog(commands.Cog):
    """OKX相关命令（仅保留价格查询功能）"""
    def __init__(self, bot: commands.Bot):
        from app.services.okx.state_cache import OKXStateCache
        self.bot = bot
        self.okx_cache = OKXStateCache()
        self.okx_cache.start()

    @app_commands.command(name="okx_price", description="获取币种实时价格")
    async def okx_price(self, interaction: discord.Interaction, symbol: str):
        """获取指定币种的实时价格"""
        price = self.okx_cache.get_price(symbol)
        if price:
            await interaction.response.send_message(f"{symbol} 当前价格: {price}")
        else:
            await interaction.response.send_message(f"无法获取 {symbol} 的价格，请检查币种名称是否正确（例如：BTC-USDT-SWAP）")

    @app_commands.command(name="price", description="REST 获取最新成交价")
    async def price(self, interaction: discord.Interaction, inst_id: str):
        p = self.get_price(inst_id)
        await interaction.response.send_message(str(p) if p else "查询失败")

    @app_commands.command(name="okx_sub", description="订阅WS实时报价")
    async def okx_sub(self, interaction: discord.Interaction, inst_id: str):
        # 按需启动
        if not self.ws.thread or not self.ws.thread.is_alive():
            self.ws.start()
        self.ws.subscribe(inst_id)
        await interaction.response.send_message(f"已订阅 {inst_id}")

    @app_commands.command(name="okx_unsub", description="取消WS订阅")
    async def okx_unsub(self, interaction: discord.Interaction, inst_id: str):
        self.ws.unsubscribe(inst_id)
        await interaction.response.send_message(f"已取消订阅 {inst_id}")

class MonitorCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        from app.config.settings import get_settings
        from app.config.trader_config import TraderConfig
        from app.services.ai.deepseek import DeepseekClient
        self.settings = get_settings()
        self.trader_config = TraderConfig()
        self.ai = DeepseekClient()
        from app.services.membership.store import MembershipStore
        # 复用membership.db，也可分表
        self.store = MembershipStore()
        # 绑定OKX价格缓存（只用于获取实时币价）
        from app.services.okx.state_cache import OKXStateCache
        self.okx_cache = OKXStateCache()
        self.okx_cache.start()

    async def cog_load(self):
        # 在cog加载时启动周期任务，并设置间隔
        interval = max(5, int(self.settings.OKX_POLL_INTERVAL_SEC))
        self._periodic_compute.change_interval(seconds=interval)
        if not self._periodic_compute.is_running():
            self._periodic_compute.start()
        
        # 显示配置信息
        traders = self.trader_config.get_all_traders()
        print(f'[Monitor] ✅ MonitorCog 已加载 - 价格轮询间隔: {interval}秒')
        if traders:
            print(f'[Monitor] 📋 已配置 {len(traders)} 个带单员:')
            for trader in traders:
                print(f'  - {trader.get("name", trader["id"])} (ID: {trader["id"]}, 频道ID: {trader["channel_id"]})')
        else:
            print(f'[Monitor] ⚠️ 未配置任何带单员，请在 .env 中设置 TRADER_CONFIG')

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # 不拦截自身
        if message.author.bot:
            return
        
        channel_id = str(message.channel.id)
        
        # 检查频道是否有对应的带单员配置
        trader = self.trader_config.get_trader_by_channel_id(channel_id)
        if not trader:
            # 调试：显示所有配置的频道ID
            if hasattr(self, '_debug_logged') and not self._debug_logged:
                all_traders = self.trader_config.get_all_traders()
                if all_traders:
                    channel_ids = [t['channel_id'] for t in all_traders]
                    print(f'[Monitor] 🔍 调试: 当前消息频道ID {channel_id} 不在监控列表中')
                    print(f'[Monitor] 🔍 调试: 已配置的频道ID: {channel_ids}')
                else:
                    print(f'[Monitor] ⚠️ 调试: 未配置任何带单员，无法监控任何频道')
                self._debug_logged = True
            return  # 该频道没有配置带单员，跳过
        
        trader_id = trader['id']
        trader_name = trader.get('name', trader_id)
        
        # 检测到频道消息日志
        print(f'[Monitor] 📨 检测到频道消息 - 带单员: {trader_name}({trader_id}), 频道ID: {channel_id}, 用户: {message.author.name}')
        
        if not message.content or not self.settings.MONITOR_PARSE_ENABLED:
            return
        if not self.ai.available():
            return
        
        # 检查是否是回复/引用消息，如果是，需要特别关注
        is_reply = message.reference is not None
        full_content = message.content
        
        # 如果是回复消息，在内容前添加提示
        if is_reply:
            full_content = f"[回复消息] {message.content}"
            print(f'[Monitor] 💬 检测到回复消息，重点关注止盈止损信息')
        
        # 使用Deepseek解析交易信息
        data = self.ai.extract_trade(full_content)
        if not isinstance(data, dict) or not data:
            # 检查消息是否包含出局/止盈/止损关键词，如果包含但未提取到，记录日志
            exit_keywords = ['出局', '止盈', '止损', '获利', '亏损', '剩余', '继续持有', '设置止损', '成本价']
            if any(keyword in message.content for keyword in exit_keywords):
                print(f'[Monitor] ⚠️ 消息包含出局/止盈/止损关键词，但Deepseek未提取到信息')
                print(f'[Monitor] ⚠️ 原始消息: {message.content[:200]}')
            if is_reply:
                print(f'[Monitor] ⚠️ 回复消息中未提取到交易信息，已跳过')
            return
        
        # 存入数据库：按 trades / updates 分流
        import sqlite3, time
        con = sqlite3.connect(self.store.db_path)
        try:
            now = int(time.time())
            if data.get('type') == 'entry':
                # 提取到入场信号日志
                symbol = data.get('symbol', 'N/A')
                side = data.get('side', 'N/A')
                entry_price = data.get('entry_price', 'N/A')
                take_profit = data.get('take_profit', 'N/A')
                stop_loss = data.get('stop_loss', 'N/A')
                print(f'[Monitor] ✅ 提取到入场信号 - 带单员: {trader_name}')
                print(f'  📊 交易对: {symbol} | 方向: {side.upper()}')
                print(f'  📍 进场点位: {entry_price}')
                print(f'  🎯 止盈点位: {take_profit}')
                print(f'  🛑 止损点位: {stop_loss}')
                # 创建表（如果不存在），添加trader_id字段
                con.execute(
                    """
                    CREATE TABLE IF NOT EXISTS trades (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        trader_id TEXT,
                        source_message_id TEXT,
                        channel_id TEXT,
                        user_id TEXT,
                        symbol TEXT,
                        side TEXT,
                        entry_price REAL,
                        take_profit REAL,
                        stop_loss REAL,
                        confidence REAL,
                        created_at INTEGER
                    )
                    """
                )
                # 如果表已存在但没有trader_id字段，添加它
                try:
                    con.execute("ALTER TABLE trades ADD COLUMN trader_id TEXT")
                except sqlite3.OperationalError:
                    pass  # 字段已存在
                
                con.execute(
                    """
                    INSERT INTO trades(trader_id, source_message_id, channel_id, user_id, symbol, side, entry_price, take_profit, stop_loss, confidence, created_at)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (trader_id, str(message.id), channel_id, str(message.author.id), data.get('symbol'), data.get('side'), data.get('entry_price'), data.get('take_profit'), data.get('stop_loss'), data.get('confidence'), now)
                )
                trade_id = con.execute("SELECT last_insert_rowid()").fetchone()[0]
                
                # 立即计算状态并保存
                symbol = data.get('symbol')
                if symbol:
                    current_price = self.okx_cache.get_price(symbol)
                    if current_price:
                        side = data.get('side')
                        entry_price = data.get('entry_price')
                        take_profit = data.get('take_profit')
                        stop_loss = data.get('stop_loss')
                        status, pnl_points, pnl_percent = self._compute_trade_status(
                            symbol, side, entry_price, take_profit, stop_loss, current_price
                        )
                        self._upsert_trade_status(con, trade_id, status, pnl_points, pnl_percent, current_price)
                        print(f'[Monitor] 💰 已计算初始状态 - 当前价: {current_price}, 状态: {status}, 盈亏: {pnl_points}')
                
                con.commit()
            elif data.get('type') == 'update':
                # 提取到更新信号日志
                status = data.get('status', 'N/A')
                pnl_points = data.get('pnl_points', 'N/A')
                print(f'[Monitor] ✅ 提取到更新信号 - 带单员: {trader_name}')
                print(f'  📈 状态: {status}')
                if pnl_points and pnl_points != 'N/A':
                    print(f'  💰 盈亏点数: {pnl_points}')
                
                # 确保表存在
                con.execute(
                    """
                    CREATE TABLE IF NOT EXISTS trade_updates (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        trader_id TEXT,
                        trade_ref_id INTEGER,
                        source_message_id TEXT,
                        channel_id TEXT,
                        user_id TEXT,
                        text TEXT,
                        pnl_points REAL,
                        status TEXT,
                        created_at INTEGER
                    )
                    """
                )
                try:
                    con.execute("ALTER TABLE trade_updates ADD COLUMN trader_id TEXT")
                except sqlite3.OperationalError:
                    pass
                
                # 尝试找到最近的活跃交易单（未结束的）
                cur = con.execute(
                    """
                    SELECT id, entry_price, take_profit, stop_loss, side, symbol FROM trades
                    WHERE trader_id=? AND channel_id=?
                    AND id NOT IN (
                        SELECT DISTINCT trade_ref_id FROM trade_updates 
                        WHERE status IN ('已止盈', '已止损', '带单主动止盈', '带单主动止损') 
                        AND trade_ref_id IS NOT NULL
                    )
                    ORDER BY created_at DESC LIMIT 1
                    """,
                    (trader_id, channel_id)
                )
                latest_trade = cur.fetchone()
                trade_ref_id = latest_trade[0] if latest_trade else None
                
                # 保存更新记录
                con.execute(
                    """
                    INSERT INTO trade_updates(trader_id, trade_ref_id, source_message_id, channel_id, user_id, text, pnl_points, status, created_at)
                    VALUES(?,?,?,?,?,?,?,?,?)
                    """,
                    (trader_id, trade_ref_id, str(message.id), channel_id, str(message.author.id), message.content, data.get('pnl_points'), data.get('status'), now)
                )
                
                # 如果找到了对应的交易单，更新其状态
                if trade_ref_id and latest_trade:
                    trade_id, entry_price, take_profit, stop_loss, side, symbol = latest_trade
                    
                    # 根据状态类型判断最终状态
                    update_status = data.get('status', '')
                    
                    # 判断是否为最终状态（已止盈、已止损等）
                    final_statuses = ['已止盈', '已止损', '带单主动止盈', '带单主动止损']
                    is_final_status = update_status in final_statuses
                    
                    # 如果是部分出局，交易单仍然活跃，但需要更新状态
                    if '部分' in update_status or '部分出局' in update_status:
                        # 部分出局：交易单仍然活跃，但状态显示为部分出局
                        # 获取当前价格计算剩余部分的盈亏
                        current_price = self.okx_cache.get_price(symbol)
                        if current_price:
                            # 计算剩余部分的盈亏（基于当前价格）
                            if side == 'long':
                                remaining_pnl = current_price - entry_price
                            else:  # short
                                remaining_pnl = entry_price - current_price
                            
                            remaining_pnl_percent = (remaining_pnl / entry_price) * 100 if entry_price > 0 else 0
                            
                            # 更新状态为部分出局，但交易单仍然活跃
                            self._upsert_trade_status(con, trade_id, update_status, remaining_pnl, remaining_pnl_percent, current_price)
                            print(f'[Monitor] 💰 部分出局 - 剩余部分盈亏: {remaining_pnl:.2f}点 ({remaining_pnl_percent:.2f}%)')
                    elif is_final_status:
                        # 最终状态：已止盈/已止损，交易单结束
                        # 使用更新消息中的盈亏点数，如果没有则计算
                        final_pnl = data.get('pnl_points')
                        if final_pnl is None or final_pnl == 'N/A':
                            # 如果没有提供盈亏点数，尝试从当前价格计算
                            current_price = self.okx_cache.get_price(symbol)
                            if current_price:
                                if side == 'long':
                                    final_pnl = current_price - entry_price
                                else:  # short
                                    final_pnl = entry_price - current_price
                            else:
                                final_pnl = 0
                        
                        final_pnl_percent = (final_pnl / entry_price) * 100 if entry_price > 0 else 0
                        self._upsert_trade_status(con, trade_id, update_status, final_pnl, final_pnl_percent, None)
                        print(f'[Monitor] ✅ 交易单已结束 - 状态: {update_status}, 盈亏: {final_pnl:.2f}点 ({final_pnl_percent:.2f}%)')
                    else:
                        # 其他更新状态（如浮盈、浮亏等），继续计算实时状态
                        current_price = self.okx_cache.get_price(symbol)
                        if current_price:
                            status, pnl_points, pnl_percent = self._compute_trade_status(
                                symbol, side, entry_price, take_profit, stop_loss, current_price
                            )
                            self._upsert_trade_status(con, trade_id, status, pnl_points, pnl_percent, current_price)
                
                con.commit()
        finally:
            con.close()

    @tasks.loop(seconds=5.0)
    async def _periodic_compute(self):
        """定期计算交易状态：结合实时币价和Deepseek解析的数据"""
        import sqlite3
        import time
        try:
            con = sqlite3.connect(self.store.db_path)
            try:
                # 确保trades表存在
                con.execute(
                    """
                    CREATE TABLE IF NOT EXISTS trades (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        trader_id TEXT,
                        source_message_id TEXT,
                        channel_id TEXT,
                        user_id TEXT,
                        symbol TEXT,
                        side TEXT,
                        entry_price REAL,
                        take_profit REAL,
                        stop_loss REAL,
                        confidence REAL,
                        created_at INTEGER
                    )
                    """
                )
                con.execute(
                    """
                    CREATE TABLE IF NOT EXISTS trade_updates (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        trader_id TEXT,
                        trade_ref_id INTEGER,
                        source_message_id TEXT,
                        channel_id TEXT,
                        user_id TEXT,
                        text TEXT,
                        pnl_points REAL,
                        status TEXT,
                        created_at INTEGER
                    )
                    """
                )
                con.commit()
                
                # 获取所有活跃的交易单（未结束的）
                # 排除已结束的交易单（已止盈、已止损、带单主动止盈、带单主动止损）
                cur = con.execute(
                            """
                            SELECT t.id, t.trader_id, t.channel_id, t.symbol, t.side, t.entry_price, t.take_profit, t.stop_loss
                            FROM trades t
                            WHERE t.id NOT IN (
                                SELECT DISTINCT trade_ref_id FROM trade_updates 
                                WHERE status IN ('已止盈', '已止损', '带单主动止盈', '带单主动止损') 
                                AND trade_ref_id IS NOT NULL
                            )
                            AND t.id NOT IN (
                                SELECT trade_id FROM trade_status_detail
                                WHERE status IN ('已止盈', '已止损', '带单主动止盈', '带单主动止损')
                            )
                            ORDER BY t.created_at DESC
                            """
                )
                active_trades = cur.fetchall()
                
                for trade_row in active_trades:
                    trade_id, trader_id, channel_id, symbol, side, entry_price, take_profit, stop_loss = trade_row
                    
                    # 检查是否有部分出局的更新记录
                    partial_exit = con.execute(
                        """
                        SELECT status, pnl_points FROM trade_updates
                        WHERE trade_ref_id=? 
                        AND (status LIKE '%部分%' OR status LIKE '%部分出局%')
                        ORDER BY created_at DESC LIMIT 1
                        """,
                        (trade_id,)
                    ).fetchone()
                    
                    # 如果已经有部分出局记录，检查状态是否应该更新
                    if partial_exit:
                        # 部分出局后，继续计算剩余部分的实时状态
                        current_price = self.okx_cache.get_price(symbol)
                        if current_price:
                            # 计算剩余部分的盈亏
                            if side == 'long':
                                remaining_pnl = current_price - entry_price
                            else:  # short
                                remaining_pnl = entry_price - current_price
                            
                            remaining_pnl_percent = (remaining_pnl / entry_price) * 100 if entry_price > 0 else 0
                            
                            # 检查是否触发止盈/止损
                            final_status = None
                            if side == 'long':
                                if take_profit and current_price >= take_profit:
                                    final_status = "已止盈"
                                elif stop_loss and current_price <= stop_loss:
                                    final_status = "已止损"
                            else:  # short
                                if take_profit and current_price <= take_profit:
                                    final_status = "已止盈"
                                elif stop_loss and current_price >= stop_loss:
                                    final_status = "已止损"
                            
                            if final_status:
                                # 触发止盈/止损，更新为最终状态
                                self._upsert_trade_status(con, trade_id, final_status, remaining_pnl, remaining_pnl_percent, current_price)
                            else:
                                # 继续显示部分出局状态，但更新剩余部分的盈亏
                                status_text = partial_exit[0]  # 使用部分出局的状态文本
                                self._upsert_trade_status(con, trade_id, status_text, remaining_pnl, remaining_pnl_percent, current_price)
                        continue
                    
                    # 获取实时价格
                    current_price = self.okx_cache.get_price(symbol)
                    if not current_price:
                        continue
                    
                    # 计算状态（基于Deepseek解析的数据和实时币价）
                    status, pnl_points, pnl_percent = self._compute_trade_status(
                        symbol, side, entry_price, take_profit, stop_loss, 
                        current_price
                    )
                    
                    # 更新交易单状态
                    self._upsert_trade_status(con, trade_id, status, pnl_points, pnl_percent, current_price)
                
                con.commit()
            finally:
                con.close()
        except Exception as e:
            print(f"Monitor状态计算异常: {e}")

    def _compute_trade_status(self, symbol: str, side: str, entry_price: float, 
                             take_profit: float, stop_loss: float, 
                             current_price: float):
        """计算交易单状态：基于Deepseek解析的数据和实时币价
        
        只使用Deepseek从Discord消息中解析出的进场价格、止盈、止损，
        结合实时币价计算当前状态
        """
        if not current_price or not entry_price:
            return ("未进场", None, None)
        
        # 计算盈亏
        if side == 'long':
            pnl_points = current_price - entry_price
            # 检查是否触发止盈/止损
            if take_profit and current_price >= take_profit:
                pnl_percent = (pnl_points / entry_price) * 100 if entry_price > 0 else 0
                return ("已止盈", round(pnl_points, 2), round(pnl_percent, 2))
            elif stop_loss and current_price <= stop_loss:
                pnl_percent = (pnl_points / entry_price) * 100 if entry_price > 0 else 0
                return ("已止损", round(pnl_points, 2), round(pnl_percent, 2))
        else:  # short
            pnl_points = entry_price - current_price
            # 检查是否触发止盈/止损
            if take_profit and current_price <= take_profit:
                pnl_percent = (pnl_points / entry_price) * 100 if entry_price > 0 else 0
                return ("已止盈", round(pnl_points, 2), round(pnl_percent, 2))
            elif stop_loss and current_price >= stop_loss:
                pnl_percent = (pnl_points / entry_price) * 100 if entry_price > 0 else 0
                return ("已止损", round(pnl_points, 2), round(pnl_percent, 2))
        
        # 计算浮盈/浮亏
        pnl_percent = (pnl_points / entry_price) * 100 if entry_price > 0 else 0
        if pnl_points > 0:
            status = "浮盈"
        elif pnl_points < 0:
            status = "浮亏"
        else:
            status = "持平"
        
        return (status, round(pnl_points, 2), round(pnl_percent, 2))

    def _upsert_status(self, con, channel_id: str, trader_id: str, status: str = None, pnl_points: float = None):
        """更新频道状态（旧方法，保留兼容性）"""
        import sqlite3
        cur = con.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS trade_status (
                channel_id TEXT PRIMARY KEY,
                trader_id TEXT,
                last_state TEXT,
                last_pnl_points REAL,
                updated_at INTEGER
            )
            """
        )
        try:
            con.execute("ALTER TABLE trade_status ADD COLUMN trader_id TEXT")
        except sqlite3.OperationalError:
            pass
        import time
        now = int(time.time())
        row = cur.execute("SELECT channel_id FROM trade_status WHERE channel_id=?", (channel_id,)).fetchone()
        if row:
            cur.execute("UPDATE trade_status SET trader_id=?, last_state=?, last_pnl_points=?, updated_at=? WHERE channel_id=?",
                        (trader_id, status, pnl_points, now, channel_id))
        else:
            cur.execute("INSERT INTO trade_status(channel_id, trader_id, last_state, last_pnl_points, updated_at) VALUES(?,?,?,?,?)",
                        (channel_id, trader_id, status, pnl_points, now))
    
    def _upsert_trade_status(self, con, trade_id: int, status: str, pnl_points: float = None, 
                            pnl_percent: float = None, current_price: float = None):
        """更新单个交易单的状态"""
        cur = con.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS trade_status_detail (
                trade_id INTEGER PRIMARY KEY,
                status TEXT,
                pnl_points REAL,
                pnl_percent REAL,
                current_price REAL,
                updated_at INTEGER
            )
            """
        )
        import time
        now = int(time.time())
        cur.execute(
            """
            INSERT INTO trade_status_detail(trade_id, status, pnl_points, pnl_percent, current_price, updated_at)
            VALUES(?,?,?,?,?,?)
            ON CONFLICT(trade_id) DO UPDATE SET
                status=excluded.status,
                pnl_points=excluded.pnl_points,
                pnl_percent=excluded.pnl_percent,
                current_price=excluded.current_price,
                updated_at=excluded.updated_at
            """,
            (trade_id, status, pnl_points, pnl_percent, current_price, now)
        )

def create_discord_bot(token, config=None):
    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix='/', intents=intents)
    return bot

def setup_discord_bot(bot, token):
    @bot.event
    async def setup_hook():
        # 注册 Cogs 并同步命令
        try:
            # 先注册MembershipCog，因为它需要注册持久化视图
            membership_cog = MembershipCog(bot)
            await bot.add_cog(membership_cog)
            await bot.add_cog(OKXCog(bot))
            await bot.add_cog(MonitorCog(bot))
            synced = await bot.tree.sync()
            print(f'[Discord] ✅ 同步了 {len(synced)} 个斜杠命令')
        except Exception as e:
            print(f'[Discord] ❌ setup_hook 初始化出错: {e}')

    @bot.event
    async def on_ready():
        print(f'[Discord] ✅ {bot.user} 已成功登录！')

    @bot.event
    async def on_message(message):
        if message.author == bot.user:
            await bot.process_commands(message)
            return
        await bot.process_commands(message)

    @bot.tree.command(name='ping', description='检查机器人延迟')
    async def ping(interaction: discord.Interaction):
        latency = round(bot.latency * 1000)
        await interaction.response.send_message(f'pong! in {latency}ms')

    return bot
