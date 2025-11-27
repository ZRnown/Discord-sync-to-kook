import sqlite3
import time
import aiohttp
import os
from typing import Optional
from app.config.settings import get_settings

class ChannelMirror:
    def __init__(self):
        self.settings = get_settings()
        from app.services.membership.store import MembershipStore
        self.store = MembershipStore()
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
            dc_id = str(discord_channel.id)
            existed = self.get_mapped(dc_id)
            if existed:
                return existed
            # Build name with optional prefix
            name = discord_channel.name
            prefix = (self.settings.MIRROR_CHANNEL_PREFIX or '').strip()
            if prefix:
                name = f"{prefix}{name}"
            # Try to reuse existing KOOK channel (防止重复创建)
            kc_id = await self._find_existing_kook_channel(name)
            if not kc_id:
                # Create text channel in KOOK when no existing channel can be reused
                kc_id = await self._create_kook_text_channel(name)
            if kc_id:
                dc_cat = str(discord_channel.category_id) if getattr(discord_channel, 'category_id', None) else None
                self.save_mapping(dc_id, kc_id, dc_cat, None, discord_channel.name)
                print(f"[Mirror] 创建并映射频道: DC#{discord_channel.name} -> KOOK:{kc_id}")
                return kc_id
            return None
        except Exception as e:
            print(f"[Mirror] ensure_mapped 异常: {e}")
            return None

    async def _create_kook_text_channel(self, name: str) -> Optional[str]:
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
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as resp:
                    data = await resp.json()
                    if resp.status == 200 and data.get('code') == 0:
                        kid = str(data.get('data', {}).get('id') or data.get('data', {}).get('channel_id'))
                        if kid:
                            return kid
                        print(f"[Mirror] 创建频道返回无ID: {data}")
                    else:
                        print(f"[Mirror] 创建频道失败 status={resp.status} body={data}")
        except Exception as e:
            print(f"[Mirror] 创建频道请求异常: {e}")
        return None

    async def _find_existing_kook_channel(self, name: str) -> Optional[str]:
        """Try to find an existing KOOK channel with the same name to avoid duplicates."""
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
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as resp:
                    data = await resp.json()
                    if resp.status == 200 and data.get('code') == 0:
                        # KOOK 可能返回 data.items 或 data
                        channels = data.get('data', {}).get('items') or data.get('data', [])
                        for ch in channels:
                            if str(ch.get('name')) == name:
                                kid = ch.get('id') or ch.get('channel_id')
                                if kid:
                                    print(f"[Mirror] 复用已有 KOOK 频道 {kid} ({name})")
                                    return str(kid)
                    else:
                        print(f"[Mirror] 查询频道列表失败 status={resp.status} body={data}")
        except Exception as e:
            print(f"[Mirror] 查询现有频道异常: {e}")
        return None
