"""
初始化用户脚本
用于创建第一个管理员用户
"""
import sqlite3
import hashlib
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.services.membership.store import MembershipStore

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def init_user(username: str, password: str):
    """创建初始用户"""
    store = MembershipStore()
    user_db_path = os.path.join(os.path.dirname(store.db_path), "users.db")
    
    con = sqlite3.connect(user_db_path)
    try:
        # 创建表
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at INTEGER,
                updated_at INTEGER
            )
            """
        )
        
        # 检查用户是否已存在
        cur = con.execute("SELECT id FROM users WHERE username=?", (username,))
        if cur.fetchone():
            print(f"用户 '{username}' 已存在")
            return False
        
        # 创建用户
        import time
        now = int(time.time())
        password_hash = hash_password(password)
        con.execute(
            "INSERT INTO users(username, password_hash, created_at, updated_at) VALUES(?,?,?,?)",
            (username, password_hash, now, now)
        )
        con.commit()
        print(f"✅ 用户 '{username}' 创建成功")
        return True
    finally:
        con.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python -m app.api.init_user <username> <password>")
        sys.exit(1)
    
    username = sys.argv[1]
    password = sys.argv[2]
    init_user(username, password)

