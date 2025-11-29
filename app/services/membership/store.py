import sqlite3
import time
from typing import Optional, Dict
from app.config.settings import get_settings

class MembershipStore:
    def __init__(self):
        self.settings = get_settings()
        self.db_path = self.settings.MEMBERSHIP_DB_PATH
        self._init_db()

    def _init_db(self):
        import os
        # 确保数据库目录存在
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        con = sqlite3.connect(self.db_path)
        try:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    used_trial INTEGER DEFAULT 0,
                    trial_start INTEGER,
                    trial_end INTEGER,
                    member_end INTEGER
                )
                """
            )
            con.commit()
        finally:
            con.close()

    def get_user(self, user_id: str) -> Dict:
        con = sqlite3.connect(self.db_path)
        try:
            cur = con.execute("SELECT user_id, used_trial, trial_start, trial_end, member_end FROM users WHERE user_id=?", (user_id,))
            row = cur.fetchone()
            if not row:
                return {"user_id": user_id, "used_trial": 0, "trial_start": None, "trial_end": None, "member_end": None}
            return {
                "user_id": row[0],
                "used_trial": int(row[1] or 0),
                "trial_start": row[2],
                "trial_end": row[3],
                "member_end": row[4],
            }
        finally:
            con.close()

    def upsert_user(self, data: Dict):
        con = sqlite3.connect(self.db_path)
        try:
            con.execute(
                """
                INSERT INTO users(user_id, used_trial, trial_start, trial_end, member_end) VALUES(?,?,?,?,?)
                ON CONFLICT(user_id) DO UPDATE SET
                  used_trial=excluded.used_trial,
                  trial_start=excluded.trial_start,
                  trial_end=excluded.trial_end,
                  member_end=excluded.member_end
                """,
                (data["user_id"], data.get("used_trial", 0), data.get("trial_start"), data.get("trial_end"), data.get("member_end"))
            )
            con.commit()
        finally:
            con.close()

    def set_trial(self, user_id: str, duration_hours: int):
        now = int(time.time())
        end_ts = now + duration_hours * 3600
        user = self.get_user(user_id)
        user.update({"used_trial": 1, "trial_start": now, "trial_end": end_ts})
        self.upsert_user(user)
        return user

    def set_member(self, user_id: str, days: int):
        now = int(time.time())
        add_secs = days * 86400
        user = self.get_user(user_id)
        cur_end = user.get("member_end") or now
        if cur_end < now:
            cur_end = now
        user.update({"member_end": cur_end + add_secs})
        self.upsert_user(user)
        return user

    def clear_member(self, user_id: str):
        user = self.get_user(user_id)
        user.update({"member_end": None})
        self.upsert_user(user)
        return user

    def mark_used_trial(self, user_id: str):
        user = self.get_user(user_id)
        user.update({"used_trial": 1})
        self.upsert_user(user)
        return user
