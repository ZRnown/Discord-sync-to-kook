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
        ok, msg = self.mgr.can_start_trial(user_id)
        
        if not ok:
            await interaction.response.send_message(
                f"❌ {msg}\n\n" +
                ("• 每个会员只能获得一次体验机会\n" if "已使用" in msg else "") +
                ("• 您当前已有体验权限，请等待体验时间结束" if "进行中" in msg else ""),
                ephemeral=True
            )
            return
        
        # 开始试用
        self.mgr.start_trial(user_id)
        
        # 分配会员角色（如果有配置）
        if isinstance(interaction.user, discord.Member) and self.settings.MEMBER_ROLE_ID:
            try:
                role = interaction.guild.get_role(int(self.settings.MEMBER_ROLE_ID))
                if role:
                    await interaction.user.add_roles(role, reason="体验权限申请")
            except Exception as e:
                print(f"[Membership] ⚠️ 分配角色失败: {e}")
        
        trial_hours = self.settings.TRIAL_DURATION_HOURS
        await interaction.response.send_message(
            f"✅ 体验权限申请成功！\n\n"
            f"🎉 您已获得 {trial_hours} 小时的体验权限\n"
            f"⏰ 体验时间结束后，权限将自动移除",
            ephemeral=True
        )
        print(f'[Membership] ✅ 用户 {interaction.user.name}({user_id}) 申请体验权限成功')

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
        self.bot.add_view(TrialView(self.mgr, self.settings))
        # 启动定期检查任务
        if not self._check_expired.is_running():
            self._check_expired.start()
        print('[Membership] ✅ MembershipCog 已加载')

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
        
        # 创建视图（包含按钮）
        view = TrialView(self.mgr, self.settings)
        
        try:
            await target_channel.send(embed=embed, view=view)
            await interaction.response.send_message(f"✅ 体验权限申请消息已发送到 {target_channel.mention}", ephemeral=True)
            print(f'[Membership] ✅ 管理员 {interaction.user.name} 在频道 {target_channel.name} 发送了体验权限申请消息')
        except Exception as e:
            await interaction.response.send_message(f"❌ 发送失败: {e}", ephemeral=True)
            print(f'[Membership] ❌ 发送体验权限申请消息失败: {e}')

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
        print(f'[Monitor] ✅ MonitorCog 已加载 - 价格轮询间隔: {interval}秒')

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # 不拦截自身
        if message.author.bot:
            return
        
        channel_id = str(message.channel.id)
        
        # 检查频道是否有对应的带单员配置
        trader = self.trader_config.get_trader_by_channel_id(channel_id)
        if not trader:
            return  # 该频道没有配置带单员，跳过
        
        trader_id = trader['id']
        trader_name = trader.get('name', trader_id)
        
        # 检测到频道消息日志
        print(f'[Monitor] 📨 检测到频道消息 - 带单员: {trader_name}({trader_id}), 频道ID: {channel_id}, 用户: {message.author.name}')
        
        if not message.content or not self.settings.MONITOR_PARSE_ENABLED:
            return
        if not self.ai.available():
            return
        
        # 使用Deepseek解析交易信息
        data = self.ai.extract_trade(message.content)
        if not isinstance(data, dict) or not data:
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
                # 如果表已存在但没有trader_id字段，添加它
                try:
                    con.execute("ALTER TABLE trade_updates ADD COLUMN trader_id TEXT")
                except sqlite3.OperationalError:
                    pass  # 字段已存在
                
                con.execute(
                    """
                    INSERT INTO trade_updates(trader_id, trade_ref_id, source_message_id, channel_id, user_id, text, pnl_points, status, created_at)
                    VALUES(?,NULL,?,?,?,?,?,?,?)
                    """,
                    (trader_id, str(message.id), channel_id, str(message.author.id), message.content, data.get('pnl_points'), data.get('status'), now)
                )
                con.commit()
                # 同步到状态表（根据update标记）
                self._upsert_status(con, channel_id, trader_id, status=data.get('status'), pnl_points=data.get('pnl_points'))
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
                cur = con.execute(
                    """
                    SELECT id, trader_id, channel_id, symbol, side, entry_price, take_profit, stop_loss
                    FROM trades
                    WHERE id NOT IN (
                        SELECT DISTINCT trade_ref_id FROM trade_updates 
                        WHERE status IN ('已止盈', '已止损', '带单主动止盈', '带单主动止损') AND trade_ref_id IS NOT NULL
                    )
                    ORDER BY created_at DESC
                    """
                )
                active_trades = cur.fetchall()
                
                for trade_row in active_trades:
                    trade_id, trader_id, channel_id, symbol, side, entry_price, take_profit, stop_loss = trade_row
                    
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
