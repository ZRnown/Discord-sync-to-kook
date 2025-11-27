import discord
from discord.ext import commands
from discord.ext import tasks
from discord import app_commands
from app.forwarding.message_forwarder import MessageForwarder
from app.forwarding.server_mirror import ChannelMirror
from app.config.settings import get_settings

class MembershipCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        from app.services.membership.manager import MembershipManager
        self.bot = bot
        self.mgr = MembershipManager()
        self.settings = get_settings()

    @app_commands.command(name="trial", description="开始试用或查询试用状态")
    async def trial(self, interaction: discord.Interaction, action: str = "start"):
        user_id = str(interaction.user.id)
        if action == "start":
            ok, msg = self.mgr.can_start_trial(user_id)
            if not ok:
                await interaction.response.send_message(f"试用不可用: {msg}", ephemeral=True)
                return
            self.mgr.start_trial(user_id)
            await interaction.response.send_message("已开通试用（6小时）", ephemeral=True)
        elif action == "status":
            st = self.mgr.get_status(user_id)
            await interaction.response.send_message(f"试用: {st['trial_status']} | 正式会员: {'是' if st['is_member'] else '否'}", ephemeral=True)
        else:
            await interaction.response.send_message("用法: /trial [start|status]", ephemeral=True)

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
            await interaction.response.send_message(f"已为 {user.mention} 添加会员 {days or 30} 天")
        elif action == 'remove':
            self.mgr.remove_member(uid)
            await interaction.response.send_message(f"已移除 {user.mention} 会员")
        elif action == 'status':
            st = self.mgr.get_status(uid)
            await interaction.response.send_message(f"试用: {st['trial_status']} | 正式会员: {'是' if st['is_member'] else '否'} | 到期: {st['member_end']}")
        else:
            await interaction.response.send_message("用法: /member [add|remove|status] ...")

class OKXCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        from app.services.okx.copy_trading import OKXCopyTrading
        from app.services.okx.market_rest import get_market_price
        from app.services.okx.market_ws import OKXMarketWS
        self.bot = bot
        self.copy = OKXCopyTrading()
        self.get_price = get_market_price
        self.ws = OKXMarketWS()

    @app_commands.command(name="okx_leaders", description="获取带单员排行榜uniqueCode")
    async def okx_leaders(self, interaction: discord.Interaction, limit: int = 5):
        codes = self.copy.get_lead_traders_rank(limit)
        await interaction.response.send_message("\n".join(codes) or "无数据")

    @app_commands.command(name="okx_current", description="带单员当前持仓")
    async def okx_current(self, interaction: discord.Interaction, unique_code: str):
        data = self.copy.get_current_positions(unique_code)
        await interaction.response.send_message(f"{len(data)} 条记录")

    @app_commands.command(name="okx_history", description="带单员平仓历史")
    async def okx_history(self, interaction: discord.Interaction, unique_code: str, limit: int = 5):
        data = self.copy.get_position_history(unique_code, limit)
        await interaction.response.send_message(f"{len(data)} 条记录")

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
        from app.services.ai.deepseek import DeepseekClient
        self.settings = get_settings()
        self.ai = DeepseekClient()
        from app.services.membership.store import MembershipStore
        # 复用membership.db，也可分表
        self.store = MembershipStore()
        # 绑定配置与OKX缓存
        from app.services.okx.state_cache import OKXStateCache
        self.bindings = self.settings.MONITOR_BINDINGS or {}
        self.okx_cache = OKXStateCache()
        self.okx_cache.start()

    async def cog_load(self):
        # 在cog加载时启动周期任务，并设置间隔
        interval = max(5, int(self.settings.OKX_POLL_INTERVAL_SEC))
        self._periodic_compute.change_interval(seconds=interval)
        if not self._periodic_compute.is_running():
            self._periodic_compute.start()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # 不拦截自身和无配置
        if message.author.bot:
            return
        if not self.settings.MONITOR_CHANNEL_IDS:
            return
        if str(message.channel.id) not in self.settings.MONITOR_CHANNEL_IDS:
            return
        if not message.content or not self.settings.MONITOR_PARSE_ENABLED:
            return
        if not self.ai.available():
            return
        data = self.ai.extract_trade(message.content)
        if not isinstance(data, dict) or not data:
            return
        # 简单存入：按 trades / updates 分流
        import sqlite3, time
        con = sqlite3.connect(self.store.db_path)
        try:
            now = int(time.time())
            if data.get('type') == 'entry':
                con.execute(
                    """
                    CREATE TABLE IF NOT EXISTS trades (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                    INSERT INTO trades(source_message_id, channel_id, user_id, symbol, side, entry_price, take_profit, stop_loss, confidence, created_at)
                    VALUES(?,?,?,?,?,?,?,?,?,?)
                    """,
                    (str(message.id), str(message.channel.id), str(message.author.id), data.get('symbol'), data.get('side'), data.get('entry_price'), data.get('take_profit'), data.get('stop_loss'), data.get('confidence'), now)
                )
                con.commit()
            elif data.get('type') == 'update':
                con.execute(
                    """
                    CREATE TABLE IF NOT EXISTS trade_updates (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                con.execute(
                    """
                    INSERT INTO trade_updates(trade_ref_id, source_message_id, channel_id, user_id, text, pnl_points, status, created_at)
                    VALUES(NULL,?,?,?,?,?,?,?)
                    """,
                    (str(message.id), str(message.channel.id), str(message.author.id), message.content, data.get('pnl_points'), data.get('status'), now)
                )
                con.commit()
                # 同步到状态表（根据update标记）
                self._upsert_status(con, str(message.channel.id), status=data.get('status'), pnl_points=data.get('pnl_points'))
        finally:
            con.close()

    @tasks.loop(seconds=5.0)
    async def _periodic_compute(self):
        import sqlite3
        try:
            if not self.bindings:
                return
            con = sqlite3.connect(self.store.db_path)
            try:
                for ch_id, cfg in self.bindings.items():
                    inst = cfg.get('inst_id')
                    code = cfg.get('unique_code')
                    price = self.okx_cache.get_price(inst)
                    positions = self.okx_cache.get_positions(code)
                    state, pnl_points = self._compute_state(inst, price, positions)
                    self._upsert_status(con, ch_id, state, pnl_points)
                con.commit()
            finally:
                con.close()
        except Exception as e:
            print(f"Monitor状态计算异常: {e}")

    def _compute_state(self, inst_id: str, price: float, positions):
        """根据当前价格与带单员持仓，输出状态与点数"""
        if price is None or not positions:
            return ("未进场", None)
        # 尝试找到该inst的持仓
        pos = None
        for p in positions:
            if str(p.get('instId')) == inst_id:
                pos = p; break
        if not pos:
            return ("未进场", None)
        try:
            open_px = float(pos.get('openAvgPx')) if pos.get('openAvgPx') is not None else None
            side = str(pos.get('posSide','')).lower()
            if open_px is None:
                return ("进行中", None)
            diff = price - open_px
            pnl_points = diff if side == 'long' else -diff
            state = "浮盈" if pnl_points > 0 else ("浮亏" if pnl_points < 0 else "持平")
            return (state, round(pnl_points, 2))
        except Exception:
            return ("进行中", None)

    def _upsert_status(self, con, channel_id: str, status: str = None, pnl_points: float = None):
        cur = con.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS trade_status (
                channel_id TEXT PRIMARY KEY,
                last_state TEXT,
                last_pnl_points REAL,
                updated_at INTEGER
            )
            """
        )
        import time
        now = int(time.time())
        # 读取现有
        row = cur.execute("SELECT channel_id FROM trade_status WHERE channel_id=?", (channel_id,)).fetchone()
        if row:
            cur.execute("UPDATE trade_status SET last_state=?, last_pnl_points=?, updated_at=? WHERE channel_id=?",
                        (status, pnl_points, now, channel_id))
        else:
            cur.execute("INSERT INTO trade_status(channel_id, last_state, last_pnl_points, updated_at) VALUES(?,?,?,?)",
                        (channel_id, status, pnl_points, now))

def create_discord_bot(token, config=None):
    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix='/', intents=intents)
    return bot

def setup_discord_bot(bot, token, kook_bot=None):
    forwarder = None
    mirror = None
    if kook_bot:
        forwarder = MessageForwarder(kook_bot)
        print("✅ 消息转发器已初始化")
        mirror = ChannelMirror()

    @bot.event
    async def setup_hook():
        # 注册 Cogs 并同步命令
        try:
            await bot.add_cog(MembershipCog(bot))
            await bot.add_cog(OKXCog(bot))
            await bot.add_cog(MonitorCog(bot))
            synced = await bot.tree.sync()
            print(f'同步了 {len(synced)} 个斜杠命令')
        except Exception as e:
            print(f'setup_hook 初始化出错: {e}')

        # 初始镜像（可选，仅提示）
        settings = get_settings()
        if settings.MIRROR_ENABLED:
            print("[Mirror] 镜像模式已启用，收到消息时将自动创建并映射 KOOK 频道")

    @bot.event
    async def on_ready():
        print(f'{bot.user} 已成功登录！')

    @bot.event
    async def on_message(message):
        if message.author == bot.user:
            await bot.process_commands(message)
            return
        if forwarder:
            try:
                override = None
                settings = get_settings()
                if settings.MIRROR_ENABLED and mirror:
                    override = await mirror.ensure_mapped(message.channel)
                await forwarder.forward_message(message, override_kook_channel_id=override)
            except Exception as e:
                print(f"❌ 转发消息时出错: {e}")
        await bot.process_commands(message)

    @bot.event
    async def on_guild_channel_create(channel):
        try:
            settings = get_settings()
            if settings.MIRROR_ENABLED and mirror:
                await mirror.ensure_mapped(channel)
        except Exception as e:
            print(f"[Mirror] 频道创建事件处理异常: {e}")

    @bot.tree.command(name='ping', description='检查机器人延迟')
    async def ping(interaction: discord.Interaction):
        latency = round(bot.latency * 1000)
        await interaction.response.send_message(f'pong! in {latency}ms')

    return bot
