#!/usr/bin/env python3
"""
修复用户数据库：确保所有用户都有 role 字段
"""
import sqlite3
import os
import sys

def fix_user_db():
    """修复用户数据库结构"""
    # 直接使用 data 目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    user_db_path = os.path.join(script_dir, "data", "users.db")
    
    print(f"📁 数据库路径: {user_db_path}")
    
    if not os.path.exists(user_db_path):
        print("❌ 数据库文件不存在")
        return False
    
    con = sqlite3.connect(user_db_path)
    try:
        # 检查表是否存在
        cur = con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
        )
        if not cur.fetchone():
            print("❌ users 表不存在")
            return False
        
        # 检查 role 字段是否存在
        cur = con.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cur.fetchall()]
        
        if 'role' not in columns:
            print("➕ 添加 role 字段...")
            try:
                con.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
                con.commit()
                print("✅ role 字段已添加")
            except sqlite3.OperationalError as e:
                print(f"⚠️  添加 role 字段失败: {e}")
        else:
            print("✅ role 字段已存在")
        
        # 检查并修复现有用户的 role
        cur = con.execute("SELECT id, username, role FROM users")
        users = cur.fetchall()
        
        if not users:
            print("ℹ️  数据库中没有用户")
            return True
        
        print(f"\n📋 找到 {len(users)} 个用户:")
        fixed_count = 0
        for user_id, username, role in users:
            if role is None or role == '':
                print(f"  🔧 修复用户: {username} (ID: {user_id})")
                con.execute("UPDATE users SET role='user' WHERE id=?", (user_id,))
                fixed_count += 1
            else:
                print(f"  ✅ {username} (ID: {user_id}) - role: {role}")
        
        if fixed_count > 0:
            con.commit()
            print(f"\n✅ 已修复 {fixed_count} 个用户的 role 字段")
        else:
            print("\n✅ 所有用户的 role 字段都正常")
        
        return True
    except Exception as e:
        print(f"❌ 修复失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        con.close()

if __name__ == "__main__":
    success = fix_user_db()
    sys.exit(0 if success else 1)

