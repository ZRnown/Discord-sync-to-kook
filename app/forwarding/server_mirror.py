import sqlite3
import time
import aiohttp
import os
from typing import Optional
from datetime import datetime
from builtins import print as builtin_print
from app.config.settings import get_settings


def print(*args, **kwargs):  # noqa: A001 - module-scoped print override
    """Inject timestamp into every log line from this module."""
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if args:
        args = (f"[{ts}] {args[0]}",) + args[1:]
    else:
        args = (f"[{ts}]",)
    return builtin_print(*args, **kwargs)

class ChannelMirror:
    def __init__(self):
        self.settings = get_settings()
        from app.services.membership.store import MembershipStore
        self.store = MembershipStore()
        self._kook_access_checked = False
        self._init_table()

    def _init_table(self):
        con = sqlite3.connect(self.store.db_path)
        try:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS channel_map (
                    discord_channel_id TEXT PRIMARY KEY,
                    kook_channel_id TEXT NOT NULL,
                    discord_category_id TEXT,
                    kook_category_id TEXT,
                    name TEXT,
                    created_at INTEGER
                )
                """
            )
            # 添加分组映射表
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS category_map (
                    discord_category_id TEXT PRIMARY KEY,
                    kook_category_id TEXT NOT NULL,
                    name TEXT,
                    created_at INTEGER
                )
                """
            )
            con.commit()
        finally:
            con.close()

    def get_mapped(self, discord_channel_id: str) -> Optional[str]:
        con = sqlite3.connect(self.store.db_path)
        try:
            cur = con.execute(
                "SELECT kook_channel_id FROM channel_map WHERE discord_channel_id=?",
                (str(discord_channel_id),),
            )
            row = cur.fetchone()
            return row[0] if row else None
        finally:
            con.close()

    def get_category_mapped(self, discord_category_id: str) -> Optional[str]:
        """获取已映射的 KOOK 分组 ID"""
        con = sqlite3.connect(self.store.db_path)
        try:
            cur = con.execute(
                "SELECT kook_category_id FROM category_map WHERE discord_category_id=?",
                (str(discord_category_id),),
            )
            row = cur.fetchone()
            return row[0] if row else None
        finally:
            con.close()

    def save_category_mapping(self, discord_category_id: str, kook_category_id: str, name: str):
        """保存分组映射"""
        con = sqlite3.connect(self.store.db_path)
        try:
            con.execute(
                """
                INSERT INTO category_map(discord_category_id, kook_category_id, name, created_at)
                VALUES(?,?,?,?)
                ON CONFLICT(discord_category_id) DO UPDATE SET
                  kook_category_id=excluded.kook_category_id,
                  name=excluded.name
                """,
                (str(discord_category_id), str(kook_category_id), name, int(time.time())),
            )
            con.commit()
        finally:
            con.close()

    def save_mapping(
        self,
        discord_channel_id: str,
        kook_channel_id: str,
        discord_category_id: Optional[str],
        kook_category_id: Optional[str],
        name: str,
    ):
        con = sqlite3.connect(self.store.db_path)
        try:
            con.execute(
                """
                INSERT INTO channel_map(discord_channel_id, kook_channel_id, discord_category_id, kook_category_id, name, created_at)
                VALUES(?,?,?,?,?,?)
                ON CONFLICT(discord_channel_id) DO UPDATE SET
                  kook_channel_id=excluded.kook_channel_id,
                  discord_category_id=excluded.discord_category_id,
                  kook_category_id=excluded.kook_category_id,
                  name=excluded.name
                """,
                (
                    str(discord_channel_id),
                    str(kook_channel_id),
                    str(discord_category_id) if discord_category_id else None,
                    str(kook_category_id) if kook_category_id else None,
                    name,
                    int(time.time()),
                ),
            )
            con.commit()
        finally:
            con.close()

    async def ensure_mapped(self, discord_channel) -> Optional[str]:
        """Return KOOK channel id, create if not exists (basic text channel)."""
        try:
            if not self.settings.MIRROR_ENABLED:
                return None
            if not self.settings.KOOK_GUILD_ID:
                print("[Mirror] KOOK_GUILD_ID 未配置，跳过镜像创建")
                return None
            if not await self._ensure_kook_access():
                return None
            dc_id = str(discord_channel.id)
            dc_name = discord_channel.name
            print(f"[Mirror] 检查频道映射: DC#{dc_name} (id={dc_id})")
            existed = self.get_mapped(dc_id)
            if existed:
                print(f"[Mirror] ✅ 数据库已有映射: DC#{dc_name} -> KOOK:{existed}")
                return existed
            # Build name with optional prefix
            name = dc_name
            prefix = (self.settings.MIRROR_CHANNEL_PREFIX or '').strip()
            if prefix:
                name = f"{prefix}{name}"
                print(f"[Mirror] 应用前缀后名称: '{name}' (原名称: '{dc_name}', 前缀: '{prefix}')")
            # 处理分组（category）
            kook_category_id = None
            dc_cat = str(discord_channel.category_id) if getattr(discord_channel, 'category_id', None) else None
            if dc_cat:
                # 获取 Discord category 对象
                category = getattr(discord_channel, 'category', None)
                # 如果 category 属性为 None，尝试通过 guild 查找
                if not category and hasattr(discord_channel, 'guild') and discord_channel.guild:
                    try:
                        category = discord_channel.guild.get_channel(int(dc_cat))
                    except (ValueError, AttributeError):
                        pass
                if category:
                    kook_category_id = await self._ensure_category_mapped(category)
                    if kook_category_id:
                        print(f"[Mirror] 频道将放入分组: DC#{category.name} -> KOOK:{kook_category_id}")
                else:
                    print(f"[Mirror] ⚠️ 无法获取 Discord 分组对象 (category_id={dc_cat})")
            
            # Try to reuse existing KOOK channel (防止重复创建)
            kc_id = await self._find_existing_kook_channel(name)
            if not kc_id:
                print(f"[Mirror] 未找到已存在频道，准备创建新频道: '{name}'")
                # Create text channel in KOOK when no existing channel can be reused
                kc_id = await self._create_kook_text_channel(name, parent_id=kook_category_id)
            if kc_id:
                self.save_mapping(dc_id, kc_id, dc_cat, kook_category_id, discord_channel.name)
                print(f"[Mirror] ✅ 保存映射: DC#{discord_channel.name} -> KOOK:{kc_id}" + (f" (分组: {kook_category_id})" if kook_category_id else ""))
                return kc_id
            return None
        except Exception as e:
            print(f"[Mirror] ensure_mapped 异常: {e}")
            return None

    async def _create_kook_text_channel(self, name: str, parent_id: Optional[str] = None) -> Optional[str]:
        """Create KOOK text channel under guild. Returns channel id or None.
        NOTE: KOOK API subject to change; we assume /api/v3/channel/create with guild_id/name/type.
        """
        from dotenv import load_dotenv
        load_dotenv()
        token = os.getenv('KOOK_BOT_TOKEN')
        url = 'https://www.kookapp.cn/api/v3/channel/create'
        headers = {
            'Authorization': f'Bot {token}',
            'Content-Type': 'application/json'
        }
        payload = {
            'guild_id': self.settings.KOOK_GUILD_ID,
            'name': name,
            'type': 1  # text
        }
        if parent_id:
            payload['parent_id'] = parent_id
        print(f"[Mirror] 正在创建 KOOK 频道: name='{name}', guild_id={self.settings.KOOK_GUILD_ID}" + (f", parent_id={parent_id}" if parent_id else ""))
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as resp:
                    data = await resp.json()
                    print(f"[Mirror] 创建频道 API 响应: status={resp.status}, code={data.get('code')}, body={data}")
                    if resp.status == 200 and data.get('code') == 0:
                        kid = str(data.get('data', {}).get('id') or data.get('data', {}).get('channel_id'))
                        if kid:
                            print(f"[Mirror] ✅ 成功创建 KOOK 频道: {kid} ({name})")
                            return kid
                        print(f"[Mirror] ⚠️ 创建频道返回无ID: {data}")
                    else:
                        print(f"[Mirror] ❌ 创建频道失败 status={resp.status} body={data}")
        except Exception as e:
            print(f"[Mirror] ❌ 创建频道请求异常: {e}")
            import traceback
            traceback.print_exc()
        return None

    async def _find_existing_kook_channel(self, name: str) -> Optional[str]:
        """Try to find an existing KOOK channel with the same name to avoid duplicates."""
        from dotenv import load_dotenv
        load_dotenv()
        token = os.getenv('KOOK_BOT_TOKEN')
        if not token:
            print(f"[Mirror] 查找频道失败: KOOK_BOT_TOKEN 未配置")
            return None
        url = 'https://www.kookapp.cn/api/v3/channel/list'
        headers = {
            'Authorization': f'Bot {token}',
            'Content-Type': 'application/json'
        }
        params = {
            'guild_id': self.settings.KOOK_GUILD_ID
        }
        print(f"[Mirror] 开始查找已存在的 KOOK 频道，目标名称: '{name}'")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as resp:
                    data = await resp.json()
                    print(f"[Mirror] 频道列表 API 响应: status={resp.status}, code={data.get('code')}")
                    if resp.status == 200 and data.get('code') == 0:
                        # KOOK 可能返回 data.items 或 data
                        channels = data.get('data', {}).get('items') or data.get('data', [])
                        if not isinstance(channels, list):
                            channels = []
                        matched = None
                        for ch in channels:
                            # 只匹配文本频道（type=1）且非分组
                            ch_type = ch.get('type', -1)
                            if ch_type != 1 or ch.get('is_category'):
                                continue
                            ch_name = str(ch.get('name', ''))
                            if ch_name == name:
                                ch_id = ch.get('id') or ch.get('channel_id')
                                if ch_id:
                                    matched = str(ch_id)
                                    break
                        if matched:
                            print(f"[Mirror] ✅ 匹配到已有 KOOK 频道 {matched} ({name})")
                            return matched
                        print(f"[Mirror] ❌ 未找到匹配的频道，将创建新频道")
                    else:
                        print(f"[Mirror] 查询频道列表失败 status={resp.status} body={data}")
        except Exception as e:
            print(f"[Mirror] 查询现有频道异常: {e}")
            import traceback
            traceback.print_exc()
        return None

    async def _ensure_category_mapped(self, discord_category) -> Optional[str]:
        """确保 Discord 分组在 KOOK 中有对应分组，返回 KOOK 分组 ID"""
        try:
            dc_cat_id = str(discord_category.id)
            dc_cat_name = discord_category.name
            
            # 检查数据库是否已有映射
            existed = self.get_category_mapped(dc_cat_id)
            if existed:
                print(f"[Mirror] ✅ 分组已有映射: DC#{dc_cat_name} -> KOOK:{existed}")
                return existed
            
            # 应用前缀（如果有）
            name = dc_cat_name
            prefix = (self.settings.MIRROR_CHANNEL_PREFIX or '').strip()
            if prefix:
                name = f"{prefix}{name}"
            
            # 查找已存在的 KOOK 分组
            kook_cat_id = await self._find_existing_kook_category(name)
            if not kook_cat_id:
                print(f"[Mirror] 未找到已存在分组，准备创建新分组: '{name}'")
                kook_cat_id = await self._create_kook_category(name)
            
            if kook_cat_id:
                self.save_category_mapping(dc_cat_id, kook_cat_id, dc_cat_name)
                print(f"[Mirror] ✅ 保存分组映射: DC#{dc_cat_name} -> KOOK:{kook_cat_id}")
                return kook_cat_id
            return None
        except Exception as e:
            print(f"[Mirror] _ensure_category_mapped 异常: {e}")
            import traceback
            traceback.print_exc()
            return None

    async def _find_existing_kook_category(self, name: str) -> Optional[str]:
        """查找已存在的 KOOK 分组（type=0 表示分组）"""
        from dotenv import load_dotenv
        load_dotenv()
        token = os.getenv('KOOK_BOT_TOKEN')
        if not token:
            return None
        url = 'https://www.kookapp.cn/api/v3/channel/list'
        headers = {
            'Authorization': f'Bot {token}',
            'Content-Type': 'application/json'
        }
        params = {
            'guild_id': self.settings.KOOK_GUILD_ID
        }
        print(f"[Mirror] 开始查找已存在的 KOOK 分组，目标名称: '{name}'")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as resp:
                    data = await resp.json()
                    if resp.status == 200 and data.get('code') == 0:
                        channels = data.get('data', {}).get('items') or data.get('data', [])
                        if not isinstance(channels, list):
                            channels = []
                        matched = None
                        for ch in channels:
                            ch_type = int(ch.get('type', -1) or -1)
                            is_cat = bool(ch.get('is_category'))
                            if not (is_cat or ch_type == 3):
                                continue
                            ch_name = str(ch.get('name', ''))
                            if ch_name == name:
                                ch_id = ch.get('id') or ch.get('channel_id')
                                if ch_id:
                                    matched = str(ch_id)
                                    break
                        if matched:
                            print(f"[Mirror] ✅ 匹配到已有 KOOK 分组 {matched} ({name})")
                            return matched
                        print(f"[Mirror] ❌ 未找到匹配的分组")
                    else:
                        print(f"[Mirror] 查询分组列表失败 status={resp.status} body={data}")
        except Exception as e:
            print(f"[Mirror] 查询现有分组异常: {e}")
            import traceback
            traceback.print_exc()
        return None

    async def _create_kook_category(self, name: str) -> Optional[str]:
        """创建 KOOK 分组，带失败回退逻辑"""
        from dotenv import load_dotenv
        load_dotenv()
        token = os.getenv('KOOK_BOT_TOKEN')
        url = 'https://www.kookapp.cn/api/v3/channel/create'
        headers = {
            'Authorization': f'Bot {token}',
            'Content-Type': 'application/json'
        }
        payload = {
            'guild_id': self.settings.KOOK_GUILD_ID,
            'name': name,
            'is_category': 1  # KOOK 文档要求只携带 guild_id/name/is_category
        }
        print(f"[Mirror] 正在创建 KOOK 分组: name='{name}', payload={payload}")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as resp:
                    data = await resp.json()
                    print(f"[Mirror] 创建分组响应: status={resp.status}, code={data.get('code')}, body={data}")
                    if resp.status == 200 and data.get('code') == 0:
                        kid = str(data.get('data', {}).get('id') or data.get('data', {}).get('channel_id'))
                        if kid:
                            print(f"[Mirror] ✅ 成功创建 KOOK 分组: {kid} ({name})")
                            return kid
                        print(f"[Mirror] ⚠️ 创建分组返回无ID: {data}")
                    else:
                        print(f"[Mirror] ❌ 创建分组失败 status={resp.status} body={data}")
        except Exception as e:
            print(f"[Mirror] ❌ 创建分组请求异常: {e}")
            import traceback
            traceback.print_exc()
        return None

    async def _ensure_kook_access(self) -> bool:
        """Check KOOK guild/token validity and cache success."""
        if self._kook_access_checked:
            return True
        guild_id = self.settings.KOOK_GUILD_ID
        if not guild_id:
            print("[Mirror] ❌ KOOK_GUILD_ID 未配置，无法访问 KOOK 服务器")
            return False
        from dotenv import load_dotenv
        load_dotenv()
        token = os.getenv('KOOK_BOT_TOKEN')
        if not token:
            print("[Mirror] ❌ KOOK_BOT_TOKEN 未配置，无法访问 KOOK 服务器")
            return False
        url = 'https://www.kookapp.cn/api/v3/channel/list'
        headers = {
            'Authorization': f'Bot {token}',
            'Content-Type': 'application/json'
        }
        params = {'guild_id': guild_id, 'page_size': 1}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as resp:
                    data = await resp.json()
                    if resp.status == 200 and data.get('code') == 0:
                        self._kook_access_checked = True
                        print(f"[Mirror] ✅ 验证 KOOK 权限通过 (guild_id={guild_id})")
                        return True
                    print(f"[Mirror] ❌ KOOK 权限校验失败 status={resp.status}, body={data}")
                    print("[Mirror] 提示: 确认 .env 中 KOOK_GUILD_ID 为 KOOK 服务器 ID，"
                          "机器人已加入该服务器且拥有建频道/发言权限。")
        except Exception as e:
            print(f"[Mirror] ❌ 验证 KOOK 权限异常: {e}")
            import traceback
            traceback.print_exc()
        self._kook_access_checked = False
        return False
