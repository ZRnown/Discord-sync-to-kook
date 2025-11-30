import requests
from typing import Optional, Dict
from app.config.settings import get_settings
import time

class OKXClient:
    def __init__(self):
        self.settings = get_settings()
        # OKX 公开 API 端点 - 使用正确的 API 域名
        self.base_url = self.settings.OKX_REST_BASE.rstrip('/')
        # 如果配置的是 www.okx.com，需要改为 api.okx.com
        if 'www.okx.com' in self.base_url:
            self.base_url = self.base_url.replace('www.okx.com', 'www.okx.com')
        # 确保使用正确的 API 端点
        if not self.base_url.startswith('http'):
            self.base_url = 'https://www.okx.com'
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        # 创建 session，设置更长的超时时间
        self.session = requests.Session()

    def request(self, method: str, endpoint: str, params: Optional[Dict] = None, timeout: int = 10, max_retries: int = 3):
        url = self.base_url + endpoint
        last_error = None
        
        for attempt in range(max_retries):
        try:
                resp = self.session.request(
                    method, 
                    url, 
                    params=params, 
                    headers=self.headers, 
                    timeout=timeout,
                    verify=True  # 保持 SSL 验证
                )
            if resp.status_code == 200:
                return resp.json()
            else:
                    print(f"[OKX] ❌ 请求失败 (尝试 {attempt + 1}/{max_retries}): {resp.status_code}, {resp.text[:200]}")
                    if attempt < max_retries - 1:
                        time.sleep(1 * (attempt + 1))  # 指数退避
                    continue
            except requests.exceptions.SSLError as e:
                last_error = e
                print(f"[OKX] ❌ SSL错误 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    # 最后一次尝试使用 verify=False（仅用于调试）
                    if attempt == max_retries - 1:
                        try:
                            print(f"[OKX] ⚠️ 最后一次尝试使用非验证模式...")
                            resp = self.session.request(
                                method, 
                                url, 
                                params=params, 
                                headers=self.headers, 
                                timeout=timeout,
                                verify=False
                            )
                            if resp.status_code == 200:
                                print(f"[OKX] ⚠️ 使用非验证模式成功获取数据（不推荐用于生产环境）")
                                return resp.json()
                        except Exception as e2:
                            print(f"[OKX] ❌ 非验证模式也失败: {e2}")
                    else:
                        time.sleep(1 * (attempt + 1))
                continue
            except requests.exceptions.Timeout:
                last_error = f"请求超时: {url}"
                print(f"[OKX] ❌ 请求超时 (尝试 {attempt + 1}/{max_retries}): {url}")
                if attempt < max_retries - 1:
                    time.sleep(1 * (attempt + 1))
                continue
            except requests.exceptions.ConnectionError as e:
                last_error = e
                print(f"[OKX] ❌ 连接错误 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(1 * (attempt + 1))
                continue
        except Exception as e:
                last_error = e
                print(f"[OKX] ❌ 网络错误 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(1 * (attempt + 1))
                continue
        
        print(f"[OKX] ❌ 所有重试均失败，最后错误: {last_error}")
            return None
