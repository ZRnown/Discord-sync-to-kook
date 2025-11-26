from typing import Dict, List, Tuple
from app.config.settings import get_settings

class ForwardConfig:
    """转发配置管理类（集中从 Settings 读取）"""
    def __init__(self):
        self.reload_config()

    def _parse_forward_rules(self) -> Dict[str, str]:
        rules_str = self.settings.FORWARD_RULES
        rules: Dict[str, str] = {}
        if not rules_str.strip():
            return rules
        try:
            pairs = rules_str.split(',')
            for pair in pairs:
                if ':' in pair:
                    discord_id, kook_id = pair.strip().split(':', 1)
                    rules[discord_id.strip()] = kook_id.strip()
        except Exception as e:
            print(f"解析转发规则失败: {e}")
            print("规则格式应为: discord_id1:kook_id1,discord_id2:kook_id2")
        return rules

    def get_kook_channel_id(self, discord_channel_id: str) -> str:
        return self.forward_rules.get(str(discord_channel_id))

    def should_forward_message(self, is_bot: bool) -> bool:
        if is_bot and not self.settings.FORWARD_BOT_MESSAGES:
            return False
        return True

    def get_forward_channels(self) -> List[Tuple[str, str]]:
        return list(self.forward_rules.items())

    def reload_config(self):
        self.settings = get_settings()
        self.forward_rules = self._parse_forward_rules()
        self.message_prefix = self.settings.MESSAGE_PREFIX
