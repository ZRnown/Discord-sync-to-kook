#!/usr/bin/env python3
"""
创建用户脚本
用于初始化管理员用户和密码
"""
import sqlite3
import hashlib
import time
import os
import sys

# 获取数据库路径
def get_user_db_path():
    """获取用户数据库路径"""
    # 尝试从环境变量获取
    db_dir = os.getenv('MEMBERSHIP_DB_PATH', 'data')
    if not os.path.isabs(db_dir):
        db_dir = os.path.join(os.path.dirname(__file__), db_dir)
    else:
        db_dir = os.path.dirname(db_dir)
    
    # 确保目录存在
    os.makedirs(db_dir, exist_ok=True)
    return os.path.join(db_dir, "users.db")

def hash_password(password: str) -> str:
    """哈希密码"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(username: str, password: str):
    """创建用户"""
    db_path = get_user_db_path()
    print(f"📁 数据库路径: {db_path}")
    
    con = sqlite3.connect(db_path)
    try:
        # 创建表
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                created_at INTEGER,
                updated_at INTEGER
            )
            """
        )
        # 添加 role 字段（如果表已存在但没有该字段）
        try:
            con.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
            con.execute("UPDATE users SET role='user' WHERE role IS NULL")
            con.commit()
        except sqlite3.OperationalError:
            # 字段已存在，但确保所有用户都有 role
            con.execute("UPDATE users SET role='user' WHERE role IS NULL")
            con.commit()
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                expires_at INTEGER NOT NULL,
                created_at INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )
        con.commit()
        print("✅ 数据库表已创建/检查")
        
        # 检查用户是否已存在
        cur = con.execute("SELECT id FROM users WHERE username=?", (username,))
        if cur.fetchone():
            print(f"⚠️  用户 '{username}' 已存在")
            response = input("是否要重置密码? (y/n): ").strip().lower()
            if response == 'y':
                now = int(time.time())
                password_hash = hash_password(password)
                con.execute(
                    "UPDATE users SET password_hash=?, updated_at=? WHERE username=?",
                    (password_hash, now, username)
                )
                con.commit()
                print(f"✅ 用户 '{username}' 的密码已重置")
                return True
            else:
                print("❌ 取消操作")
                return False
        
        # 创建新用户
        now = int(time.time())
        password_hash = hash_password(password)
        # 询问用户角色
        role = "user"
        if len(sys.argv) >= 4:
            role = sys.argv[3]
        else:
            role_input = input("用户角色 (admin/user，默认: user): ").strip().lower()
            if role_input in ["admin", "user"]:
                role = role_input
        
        con.execute(
            "INSERT INTO users(username, password_hash, role, created_at, updated_at) VALUES(?,?,?,?,?)",
            (username, password_hash, role, now, now)
        )
        con.commit()
        print(f"✅ 用户 '{username}' 创建成功")
        return True
    except Exception as e:
        print(f"❌ 创建用户失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        con.close()

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        username = sys.argv[1]
        password = sys.argv[2]
    else:
        print("=" * 50)
        print("用户创建工具")
        print("=" * 50)
        username = input("请输入用户名: ").strip()
        if not username:
            print("❌ 用户名不能为空")
            sys.exit(1)
        
        import getpass
        password = getpass.getpass("请输入密码: ").strip()
        if not password:
            print("❌ 密码不能为空")
            sys.exit(1)
        
        password_confirm = getpass.getpass("请再次输入密码确认: ").strip()
        if password != password_confirm:
            print("❌ 两次输入的密码不一致")
            sys.exit(1)
    
    create_user(username, password)

