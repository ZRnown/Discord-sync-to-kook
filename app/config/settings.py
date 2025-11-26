import os
from functools import lru_cache
from dotenv import load_dotenv

# Load .env once
load_dotenv()

class Settings:
    def __init__(self):
        self.ENABLE_DISCORD = os.getenv('ENABLE_DISCORD', 'true').lower() == 'true'
        self.ENABLE_KOOK = os.getenv('ENABLE_KOOK', 'true').lower() == 'true'
        self.DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
        self.KOOK_BOT_TOKEN = os.getenv('KOOK_BOT_TOKEN')
        self.FORWARD_RULES = os.getenv('FORWARD_RULES', '')
        self.FORWARD_BOT_MESSAGES = os.getenv('FORWARD_BOT_MESSAGES', 'false').lower() == 'true'
        self.MESSAGE_PREFIX = os.getenv('MESSAGE_PREFIX', '[Discord]')

        # Guild & Roles
        self.GUILD_ID = os.getenv('GUILD_ID')
        self.MEMBER_ROLE_ID = os.getenv('MEMBER_ROLE_ID')
        self.ADMIN_ROLE_IDS = [rid.strip() for rid in os.getenv('ADMIN_ROLE_IDS', '').split(',') if rid.strip()]

        # Membership
        self.TRIAL_ENABLED = os.getenv('TRIAL_ENABLED', 'true').lower() == 'true'
        self.TRIAL_DURATION_HOURS = int(os.getenv('TRIAL_DURATION_HOURS', '6'))
        self.TRIAL_ONCE_PER_USER = os.getenv('TRIAL_ONCE_PER_USER', 'true').lower() == 'true'
        self.MEMBERSHIP_STORE = os.getenv('MEMBERSHIP_STORE', 'sqlite')  # sqlite/json
        self.MEMBERSHIP_DB_PATH = os.getenv('MEMBERSHIP_DB_PATH', '/app/data/membership.db')

        # OKX
        self.OKX_REST_BASE = os.getenv('OKX_REST_BASE', 'https://www.okx.com')
        self.OKX_WS_URL = os.getenv('OKX_WS_URL', 'wss://ws.okx.com:8443/ws/v5/public')
        self.OKX_INST_IDS = [s.strip() for s in os.getenv('OKX_INST_IDS', 'BTC-USDT-SWAP,ETH-USDT-SWAP').split(',') if s.strip()]
        self.OKX_COPY_MONITOR_ENABLED = os.getenv('OKX_COPY_MONITOR_ENABLED', 'true').lower() == 'true'
        self.OKX_POLL_INTERVAL_SEC = float(os.getenv('OKX_POLL_INTERVAL_SEC', '5'))
        self.OKX_WS_ENABLED = os.getenv('OKX_WS_ENABLED', 'true').lower() == 'true'
        self.OKX_REST_ENABLED = os.getenv('OKX_REST_ENABLED', 'true').lower() == 'true'

        # Monitoring & AI
        self.MONITOR_CHANNEL_IDS = [cid.strip() for cid in os.getenv('MONITOR_CHANNEL_IDS', '').split(',') if cid.strip()]
        self.MONITOR_PARSE_ENABLED = os.getenv('MONITOR_PARSE_ENABLED', 'true').lower() == 'true'
        self.DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
        self.DEEPSEEK_MODEL = os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')
        self.DEEPSEEK_ENDPOINT = os.getenv('DEEPSEEK_ENDPOINT', 'https://api.deepseek.com/v1/chat/completions')

        # Monitor bindings: channelId=uniqueCode@instId;channelId2=code2@inst2
        self.MONITOR_BINDINGS = {}
        bindings_raw = os.getenv('MONITOR_BINDINGS', '').strip()
        if bindings_raw:
            parts = [p.strip() for p in bindings_raw.split(';') if p.strip()]
            for p in parts:
                if '=' in p and '@' in p:
                    ch, right = p.split('=', 1)
                    code, inst = right.split('@', 1)
                    self.MONITOR_BINDINGS[ch.strip()] = {
                        'unique_code': code.strip(),
                        'inst_id': inst.strip()
                    }

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
