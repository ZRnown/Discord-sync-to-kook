import asyncio
import aiohttp
import os
import time
import json
import mimetypes
from pathlib import Path
from typing import List, Optional
import discord
from khl import Bot as KookBot
from app.config.forward_config import ForwardConfig

class MessageForwarder:
    def __init__(self, kook_bot: KookBot):
        self.kook_bot = kook_bot
        self.config = ForwardConfig()
        self.download_dir = Path('downloads')
        self.download_dir.mkdir(exist_ok=True)
        (self.download_dir / 'images').mkdir(exist_ok=True)
        (self.download_dir / 'videos').mkdir(exist_ok=True)
        # 简易头像缓存：user_id -> kook_asset_url
        self.avatar_cache = {}
        # 翻译功能已移除

    async def forward_message(self, discord_message: discord.Message, override_kook_channel_id: Optional[str] = None) -> bool:
        try:
            if not self.config.should_forward_message(discord_message.author.bot):
                print(f"[Forward] 跳过机器人消息: author_bot={discord_message.author.bot}")
                return False
            kook_channel_id = override_kook_channel_id or self.config.get_kook_channel_id(str(discord_message.channel.id))
            if not kook_channel_id:
                print(f"[Forward] 未找到映射规则: discord_channel={discord_message.channel.id}")
                return False
            print(f"[Forward] 命中规则: {discord_message.channel.id} -> {kook_channel_id}")
            forwarded_card, embedded_attachment_ids = await self._build_forward_card(discord_message)
            success = False
            if forwarded_card:
                sent = await self._send_card_message(kook_channel_id, forwarded_card)
                if sent:
                    print(f"[Forward] 文本卡片发送完成 -> KOOK:{kook_channel_id}")
                    success = True
                else:
                    # 回退为纯文本
                    fallback = await self._build_fallback_text(discord_message)
                    if fallback:
                        await self._send_text_message(kook_channel_id, fallback)
            if discord_message.attachments:
                # 跳过已内嵌到卡片中的附件（若有）
                skip_ids = set(embedded_attachment_ids or [])
                await self._forward_attachments(discord_message, kook_channel_id, skip_ids=skip_ids)
                print(f"[Forward] 附件发送完成 -> KOOK:{kook_channel_id}")
                success = True
            return success
        except Exception as e:
            print(f"转发消息失败: {e}")
            return False

    async def _build_forward_card(self, discord_message: discord.Message) -> Optional[tuple]:
        author_name = discord_message.author.display_name
        avatar_url = await self._get_kook_avatar_url(discord_message.author)
        content = discord_message.content or ''
        if not content and not discord_message.attachments:
            return None, None

        modules = []
        # 顶部：使用 context 放置更小的头像 + 用户名
        top_elements = []
        if avatar_url:
            top_elements.append({'type': 'image', 'src': avatar_url})  # context 的 image 无需 size，展示更小
        top_elements.append({'type': 'plain-text', 'content': f"{author_name}"})
        modules.append({'type': 'context', 'elements': top_elements})

        # 中间：文本内容（如有）
        if content:
            modules.append({'type': 'section', 'text': {'type': 'kmarkdown', 'content': content}})

        # 中间：收集并内嵌媒体（多图合并展示，视频取首个）
        media_modules, embedded_ids = await self._collect_media_modules(discord_message)
        modules.extend(media_modules)

        # 底部：Discord 小图标 + 日期（小号字体）
        ts_str = self._format_cn_datetime(discord_message)
        footer_elements = []
        icon_url = os.getenv('DISCORD_ICON_URL', '').strip()
        if icon_url:
            footer_elements.append({'type': 'image', 'src': icon_url})
        footer_elements.append({'type': 'kmarkdown', 'content': f"Discord · {ts_str}"})
        modules.append({'type': 'context', 'elements': footer_elements})

        card = {'type': 'card', 'theme': 'secondary', 'modules': modules}
        return [card], embedded_ids

    async def _get_kook_avatar_url(self, user: discord.User) -> Optional[str]:
        try:
            uid = str(user.id)
            if uid in self.avatar_cache:
                return self.avatar_cache[uid]
            if not hasattr(user, 'display_avatar') or not user.display_avatar:
                return None
            src_url = str(user.display_avatar.url)
            if not src_url:
                return None
            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(src_url) as resp:
                    if resp.status != 200:
                        print(f"[Avatar] 下载失败 status={resp.status}")
                        return None
                    file_bytes = await resp.read()
                    ctype = resp.headers.get('Content-Type', 'image/png')
                    ext = '.png'
                    if 'jpeg' in ctype or 'jpg' in ctype:
                        ext = '.jpg'
                    elif 'gif' in ctype:
                        ext = '.gif'
                    elif 'webp' in ctype:
                        ext = '.webp'
            # 上传到 KOOK 资产
            from dotenv import load_dotenv
            load_dotenv()
            token = os.getenv('KOOK_BOT_TOKEN')
            upload_url = 'https://www.kookapp.cn/api/v3/asset/create'
            headers = { 'Authorization': f'Bot {token}' }
            form = aiohttp.FormData()
            form.add_field('file', file_bytes, filename=f"avatar_{uid}{ext}", content_type=ctype)
            form.add_field('type', '1')
            async with aiohttp.ClientSession() as session:
                async with session.post(upload_url, headers=headers, data=form) as response:
                    if response.status == 200:
                        resp_json = await response.json()
                        if resp_json.get('code') == 0 and resp_json.get('data', {}).get('url'):
                            url = resp_json['data']['url']
                            self.avatar_cache[uid] = url
                            print(f"[Avatar] 上传成功 user={uid}")
                            return url
                        else:
                            print(f"[Avatar] 上传返回异常: {resp_json}")
                    else:
                        print(f"[Avatar] 上传失败 HTTP={response.status}")
        except Exception as e:
            print(f"[Avatar] 处理异常: {e}")
        return None

    async def _build_fallback_text(self, discord_message: discord.Message) -> str:
        author_name = discord_message.author.display_name
        content = discord_message.content or ''
        if not content:
            return ""
        return f"{author_name}: {content}"

    async def _send_text_message(self, kook_channel_id: str, content: str):
        import os
        from dotenv import load_dotenv
        load_dotenv()
        token = os.getenv('KOOK_BOT_TOKEN')
        url = 'https://www.kookapp.cn/api/v3/message/create'
        headers = {
            'Authorization': f'Bot {token}',
            'Content-Type': 'application/json'
        }
        data = { 'target_id': kook_channel_id, 'content': content, 'type': 1 }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data) as response:
                    resp_json = await response.json()
                    if response.status == 200 and resp_json.get('code') == 0:
                        print(f"[KOOK] 文本发送成功 -> channel={kook_channel_id}")
                        return
                    print(f"⚠️ 文本发送失败: status={response.status}, body={resp_json}")
        except Exception as e:
            print(f"❌ 文本API请求异常: {e}")

    async def _send_card_message(self, kook_channel_id: str, cards: list) -> bool:
        from dotenv import load_dotenv
        load_dotenv()
        token = os.getenv('KOOK_BOT_TOKEN')
        url = 'https://www.kookapp.cn/api/v3/message/create'
        headers = {
            'Authorization': f'Bot {token}',
            'Content-Type': 'application/json'
        }
        payload = { 'target_id': kook_channel_id, 'content': json.dumps(cards), 'type': 10 }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    resp_json = await response.json()
                    if response.status == 200 and resp_json.get('code') == 0:
                        print(f"[KOOK] 卡片发送成功 -> channel={kook_channel_id}")
                        return True
                    print(f"⚠️ 卡片发送失败: status={response.status}, body={resp_json}")
        except Exception as e:
            print(f"❌ 发送卡片异常: {e}")
        return False

    async def _forward_attachments(self, discord_message: discord.Message, kook_channel_id: str, skip_ids: Optional[set] = None):
        """转发附件到KOOK"""
        skip_ids = skip_ids or set()
        for attachment in discord_message.attachments:
            if attachment.id in skip_ids:
                continue
            try:
                file_path = await self._download_attachment(attachment)
                if file_path:
                    await self._send_file_to_kook(kook_channel_id, file_path, attachment.filename)
                    await self._schedule_file_cleanup(file_path, attachment.content_type)
            except Exception as e:
                print(f"❌ 转发附件失败 {attachment.filename}: {e}")

    async def _collect_media_modules(self, discord_message: discord.Message) -> tuple:
        """上传并构建媒体模块：
        - 多张图片：合并到一个 container 内的多个 image 元素
        - 视频：仅取首个视频，使用 video 模块
        返回 (modules, embedded_attachment_ids)
        """
        images = []
        videos = []
        embedded_ids = []
        for att in discord_message.attachments:
            ctype = (att.content_type or '')
            if ctype.startswith('image/'):
                images.append(att)
            elif ctype.startswith('video/'):
                videos.append(att)

        modules = []
        # 处理图片（全部合并展示）
        if images:
            image_elements = []
            for img in images:
                url = await self._upload_attachment_and_get_url(img)
                if url:
                    image_elements.append({'type': 'image', 'src': url})
                    embedded_ids.append(img.id)
            if image_elements:
                modules.append({'type': 'container', 'elements': image_elements})

        # 处理视频（仅第一个）
        if videos:
            first_v = videos[0]
            v_url = await self._upload_attachment_and_get_url(first_v)
            if v_url:
                modules.append({'type': 'video', 'title': first_v.filename, 'src': v_url})
                embedded_ids.append(first_v.id)

        return modules, embedded_ids

    async def _upload_attachment_and_get_url(self, attachment: discord.Attachment) -> Optional[str]:
        """下载并上传单个附件到 KOOK 资产，返回 URL。"""
        try:
            file_path = await self._download_attachment(attachment)
            if not file_path:
                return None
            from dotenv import load_dotenv
            load_dotenv()
            token = os.getenv('KOOK_BOT_TOKEN')
            upload_url = 'https://www.kookapp.cn/api/v3/asset/create'
            headers = {'Authorization': f'Bot {token}'}

            content_type, _ = mimetypes.guess_type(file_path)
            if not content_type:
                content_type = 'application/octet-stream'

            file_type = 1
            if self._is_video_file(file_path):
                file_type = 2
            else:
                if not content_type.startswith('image/'):
                    file_type = 3

            async with aiohttp.ClientSession() as session:
                with open(file_path, 'rb') as f:
                    form = aiohttp.FormData()
                    form.add_field('file', f, filename=attachment.filename, content_type=content_type)
                    form.add_field('type', str(file_type))
                    async with session.post(upload_url, headers=headers, data=form) as response:
                        if response.status == 200:
                            resp_json = await response.json()
                            if resp_json.get('code') == 0 and resp_json.get('data', {}).get('url'):
                                return resp_json['data']['url']
            return None
        except Exception as e:
            print(f"❌ 上传附件失败(获取URL): {e}")
            return None

    def _format_cn_datetime(self, discord_message: discord.Message) -> str:
        try:
            ts = discord_message.created_at
            # 尝试中文格式化，如 2023年1月3日 09:27
            try:
                return ts.strftime('%Y年%-m月%-d日 %H:%M')
            except Exception:
                return ts.strftime('%Y年%m月%d日 %H:%M')
        except Exception:
            return time.strftime('%Y年%m月%d日 %H:%M', time.localtime())

    async def _download_attachment(self, attachment: discord.Attachment) -> Optional[Path]:
        try:
            content_type = attachment.content_type or ""
            if content_type.startswith('image/'):
                target_dir = self.download_dir / 'images'
            elif content_type.startswith('video/'):
                target_dir = self.download_dir / 'videos'
            else:
                target_dir = self.download_dir
            target_dir.mkdir(exist_ok=True)
            file_path = target_dir / f"{attachment.id}_{attachment.filename}"
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(attachment.url) as response:
                    if response.status == 200:
                        with open(file_path, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                f.write(chunk)
                        print(f"📥 已下载附件到 {target_dir}: {file_path.name}")
                        return file_path
                    else:
                        print(f"❌ 下载附件失败，HTTP状态码: {response.status}")
                        return None
        except Exception as e:
            print(f"❌ 下载附件异常: {e}")
            return None

    async def _send_file_to_kook(self, kook_channel_id: str, file_path: Path, original_filename: str):
        try:
            # 直接使用 KOOK API 上传

            from dotenv import load_dotenv
            load_dotenv()
            token = os.getenv('KOOK_BOT_TOKEN')

            content_type, _ = mimetypes.guess_type(file_path)
            if not content_type:
                content_type = 'application/octet-stream'

            file_size = os.path.getsize(file_path)
            if file_size > 20 * 1024 * 1024:
                await self._send_text_message(kook_channel_id, f"{self.config.message_prefix} 文件过大(>20MB): {original_filename}")
                print(f"⚠️ 文件过大 {file_size/1024/1024:.2f}MB，已发送文本通知")
                return

            upload_url = 'https://www.kookapp.cn/api/v3/asset/create'
            headers = { 'Authorization': f'Bot {token}' }

            file_type = 1
            is_video = self._is_video_file(file_path)
            if is_video:
                file_type = 2
            else:
                if not content_type.startswith('image/'):
                    file_type = 3

            async with aiohttp.ClientSession() as session:
                with open(file_path, 'rb') as f:
                    form = aiohttp.FormData()
                    form.add_field('file', f, filename=original_filename, content_type=content_type)
                    form.add_field('type', str(file_type))
                    async with session.post(upload_url, headers=headers, data=form) as response:
                        if response.status == 200:
                            resp_json = await response.json()
                            if resp_json.get('code') == 0 and resp_json.get('data', {}).get('url'):
                                file_url = resp_json['data']['url']
                                if self._is_image_file(file_path):
                                    await self._send_image_card(kook_channel_id, file_url, original_filename)
                                elif self._is_video_file(file_path):
                                    await self._send_video_card(kook_channel_id, file_url, original_filename)
                                else:
                                    await self._send_text_message(kook_channel_id, f"文件: {original_filename}\n{file_url}")
                                print(f"✅ 文件已上传并发送: {original_filename}")
                            else:
                                await self._send_text_message(kook_channel_id, f"文件上传失败: {original_filename}")
                                print(f"❌ 文件上传成功但未获取到URL: {resp_json}")
                        else:
                            await self._send_text_message(kook_channel_id, f"文件上传失败: {original_filename}")
                            print(f"❌ 上传文件到KOOK失败，HTTP状态码: {response.status}")
        except Exception as e:
            print(f"❌ 上传文件到KOOK异常: {e}")
            await self._send_text_message(kook_channel_id, f"{self.config.message_prefix} 文件上传失败: {original_filename}")

    def _is_image_file(self, file_path: Path) -> bool:
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        return file_path.suffix.lower() in image_extensions

    def _is_video_file(self, file_path: Path) -> bool:
        video_extensions = {'.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv'}
        return file_path.suffix.lower() in video_extensions

    async def _send_image_card(self, kook_channel_id: str, image_url: str, original_filename: str):
        from dotenv import load_dotenv
        load_dotenv()
        token = os.getenv('KOOK_BOT_TOKEN')
        card = {
            'type': 'card',
            'theme': 'secondary',
            'modules': [
                {'type': 'header', 'text': {'type': 'plain-text', 'content': f"图片: {original_filename}"}},
                {'type': 'container', 'elements': [{'type': 'image', 'src': image_url}]}
            ]
        }
        card_content = json.dumps([card])
        url = 'https://www.kookapp.cn/api/v3/message/create'
        headers = { 'Authorization': f'Bot {token}', 'Content-Type': 'application/json' }
        data = { 'target_id': kook_channel_id, 'content': card_content, 'type': 10 }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as response:
                if response.status == 200:
                    resp_json = await response.json()
                    if resp_json.get('code') == 0:
                        print(f"✅ 图片卡片消息已发送: {original_filename}")
                    else:
                        print(f"❌ 发送图片卡片消息失败: {resp_json}")
                        await self._send_text_message(kook_channel_id, f"图片: {original_filename}\n{image_url}")
                else:
                    print(f"❌ 发送图片卡片消息失败，HTTP状态码: {response.status}")
                    await self._send_text_message(kook_channel_id, f"{self.config.message_prefix} 图片: {original_filename}\n{image_url}")

    async def _send_video_card(self, kook_channel_id: str, video_url: str, original_filename: str):
        from dotenv import load_dotenv
        load_dotenv()
        token = os.getenv('KOOK_BOT_TOKEN')
        card = {
            'type': 'card',
            'theme': 'secondary',
            'modules': [
                {'type': 'header', 'text': {'type': 'plain-text', 'content': f"视频: {original_filename}"}},
                {'type': 'video', 'title': original_filename, 'src': video_url}
            ]
        }
        card_content = json.dumps([card])
        url = 'https://www.kookapp.cn/api/v3/message/create'
        headers = { 'Authorization': f'Bot {token}', 'Content-Type': 'application/json' }
        data = { 'target_id': kook_channel_id, 'content': card_content, 'type': 10 }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data) as response:
                if response.status == 200:
                    resp_json = await response.json()
                    if resp_json.get('code') == 0:
                        print(f"✅ 视频卡片消息已发送: {original_filename}")
                    else:
                        print(f"❌ 发送视频卡片消息失败: {resp_json}")
                        await self._send_text_message(kook_channel_id, f"视频: {original_filename}\n{video_url}")
                else:
                    print(f"❌ 发送视频卡片消息失败，HTTP状态码: {response.status}")
                    await self._send_text_message(kook_channel_id, f"{self.config.message_prefix} 视频: {original_filename}\n{video_url}")

    async def _schedule_file_cleanup(self, file_path: Path, content_type: Optional[str]):
        try:
            if content_type and content_type.startswith('image/'):
                cleanup_hours = int(os.getenv('IMAGE_CLEANUP_HOURS', '24'))
            elif content_type and content_type.startswith('video/'):
                cleanup_hours = int(os.getenv('VIDEO_CLEANUP_HOURS', '12'))
            else:
                cleanup_hours = 6
            asyncio.create_task(self._cleanup_file_after_delay(file_path, cleanup_hours * 3600))
        except Exception as e:
            print(f"❌ 安排文件清理失败: {e}")

    async def _cleanup_file_after_delay(self, file_path: Path, delay_seconds: int):
        try:
            await asyncio.sleep(delay_seconds)
            if file_path.exists():
                file_path.unlink()
                print(f"🗑️ 已清理文件: {file_path}")
        except Exception as e:
            print(f"❌ 清理文件失败: {e}")

    async def _cleanup_old_files(self):
        try:
            image_max_age = int(os.getenv('IMAGE_MAX_AGE_DAYS', '7')) * 24 * 3600
            video_max_age = int(os.getenv('VIDEO_MAX_AGE_DAYS', '3')) * 24 * 3600
            other_max_age = int(os.getenv('OTHER_MAX_AGE_DAYS', '1')) * 24 * 3600
            now = time.time()
            await self._cleanup_directory(self.download_dir / 'images', now, image_max_age)
            await self._cleanup_directory(self.download_dir / 'videos', now, video_max_age)
            await self._cleanup_directory(self.download_dir, now, other_max_age, exclude_dirs=True)
            print('✅ 定期清理完成')
        except Exception as e:
            print(f"❌ 清理过期文件失败: {e}")

    async def _cleanup_directory(self, directory: Path, now: float, max_age: int, exclude_dirs: bool = False):
        if not directory.exists() or not directory.is_dir():
            return
        try:
            deleted_count = 0
            for item in directory.iterdir():
                if exclude_dirs and item.is_dir():
                    continue
                if item.is_file():
                    mtime = item.stat().st_mtime
                    age = now - mtime
                    if age > max_age:
                        item.unlink()
                        deleted_count += 1
            if deleted_count > 0:
                print(f"🗑️ 已从 {directory} 清理 {deleted_count} 个过期文件")
        except Exception as e:
            print(f"❌ 清理目录 {directory} 失败: {e}")
