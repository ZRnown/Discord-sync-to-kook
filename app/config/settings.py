import os
from functools import lru_cache
from dotenv import load_dotenv

# Load .env once
load_dotenv()

def _env_bool(key: str, default: str = 'false') -> bool:
    """取布尔环境变量，自动 strip + lower，避免因空格导致解析失败。"""
    raw = os.getenv(key)
    if raw is None:
        raw = default
    raw = raw.strip().lower()
    if not raw:
        raw = default.strip().lower()
    return raw == 'true'

class Settings:
    def __init__(self):
        self.ENABLE_DISCORD = _env_bool('ENABLE_DISCORD', 'true')
        self.DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')

        # Guild & Roles
        self.GUILD_ID = os.getenv('GUILD_ID')
        self.MEMBER_ROLE_ID = os.getenv('MEMBER_ROLE_ID')
        self.ADMIN_ROLE_IDS = [rid.strip() for rid in os.getenv('ADMIN_ROLE_IDS', '').split(',') if rid.strip()]

        # Membership
        self.TRIAL_ENABLED = _env_bool('TRIAL_ENABLED', 'true')
        self.TRIAL_DURATION_HOURS = int(os.getenv('TRIAL_DURATION_HOURS', '6'))
        self.TRIAL_ONCE_PER_USER = _env_bool('TRIAL_ONCE_PER_USER', 'true')
        self.MEMBERSHIP_STORE = os.getenv('MEMBERSHIP_STORE', 'sqlite')  # sqlite/json
        # 默认使用相对路径 ./data/membership.db
        default_db_path = os.path.join(os.getcwd(), 'data', 'membership.db')
        self.MEMBERSHIP_DB_PATH = os.getenv('MEMBERSHIP_DB_PATH', default_db_path)

        # OKX
        self.OKX_REST_BASE = os.getenv('OKX_REST_BASE', 'https://www.okx.com')
        self.OKX_WS_URL = os.getenv('OKX_WS_URL', 'wss://ws.okx.com:8443/ws/v5/public')
        self.OKX_INST_IDS = [s.strip() for s in os.getenv('OKX_INST_IDS', 'BTC-USDT-SWAP,ETH-USDT-SWAP').split(',') if s.strip()]
        self.OKX_COPY_MONITOR_ENABLED = _env_bool('OKX_COPY_MONITOR_ENABLED', 'true')
        self.OKX_POLL_INTERVAL_SEC = float(os.getenv('OKX_POLL_INTERVAL_SEC', '5'))
        self.OKX_WS_ENABLED = _env_bool('OKX_WS_ENABLED', 'true')
        self.OKX_REST_ENABLED = _env_bool('OKX_REST_ENABLED', 'true')

        # Monitoring & AI
        self.MONITOR_CHANNEL_IDS = [cid.strip() for cid in os.getenv('MONITOR_CHANNEL_IDS', '').split(',') if cid.strip()]
        self.MONITOR_PARSE_ENABLED = _env_bool('MONITOR_PARSE_ENABLED', 'true')
        self.DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
        self.DEEPSEEK_MODEL = os.getenv('DEEPSEEK_MODEL', 'deepseek-v3.2')
        self.DEEPSEEK_ENDPOINT = os.getenv('DEEPSEEK_ENDPOINT', 'https://api.v3.cm/v1/chat/completions')
        default_log_dir = os.path.join(os.getcwd(), 'logs', 'monitor')
        self.MONITOR_LOG_DIR = os.getenv('MONITOR_LOG_DIR', default_log_dir)

        # Trader configuration: trader_id|channel_id|trader_name;trader2|channel2|name2
        # 格式：带单员ID|Discord频道ID|带单员名称
        self.TRADER_CONFIG = {}
        trader_config_raw = os.getenv('TRADER_CONFIG', '').strip()
        if trader_config_raw:
            parts = [p.strip() for p in trader_config_raw.split(';') if p.strip()]
            for p in parts:
                if '|' in p:
                    segments = [s.strip() for s in p.split('|')]
                    if len(segments) >= 2:
                        trader_id = segments[0]
                        channel_id = segments[1]
                        trader_name = segments[2] if len(segments) > 2 else trader_id
                        self.TRADER_CONFIG[trader_id] = {
                            'channel_id': channel_id,
                            'name': trader_name,
                            'id': trader_id
                        }

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
