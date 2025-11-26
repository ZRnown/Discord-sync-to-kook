import time
from typing import Tuple, Dict
from app.config.settings import get_settings
from .store import MembershipStore

class MembershipManager:
    def __init__(self):
        self.settings = get_settings()
        self.store = MembershipStore()

    def can_start_trial(self, user_id: str) -> Tuple[bool, str]:
        if not self.settings.TRIAL_ENABLED:
            return False, "试用已关闭"
        user = self.store.get_user(user_id)
        if self.settings.TRIAL_ONCE_PER_USER and user.get("used_trial"):
            return False, "试用已使用"
        trial_end = user.get("trial_end")
        now = int(time.time())
        if trial_end and trial_end > now:
            return False, "试用进行中"
        return True, "可以开始试用"

    def start_trial(self, user_id: str) -> Dict:
        return self.store.set_trial(user_id, self.settings.TRIAL_DURATION_HOURS)

    def get_status(self, user_id: str) -> Dict:
        user = self.store.get_user(user_id)
        now = int(time.time())
        status = {
            "used_trial": bool(user.get("used_trial")),
            "trial_status": "未使用",
            "trial_end": user.get("trial_end"),
            "member_end": user.get("member_end"),
            "is_member": False,
        }
        trial_end = user.get("trial_end")
        if trial_end:
            status["trial_status"] = "进行中" if trial_end > now else "已过期"
        member_end = user.get("member_end")
        if member_end and member_end > now:
            status["is_member"] = True
        return status

    def add_member(self, user_id: str, days: int) -> Dict:
        return self.store.set_member(user_id, days)

    def remove_member(self, user_id: str) -> Dict:
        return self.store.clear_member(user_id)
