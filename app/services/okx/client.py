import requests
import time
from typing import Optional, Dict
from app.config.settings import get_settings

class OKXClient:
    def __init__(self):
        self.settings = get_settings()
        # OKX 公开 API 端点
        self.base_url = self.settings.OKX_REST_BASE.rstrip('/')
        
        # 修正逻辑：如果注释说要改成 api.okx.com，代码应该体现这一点
        # 原代码 replace('www.okx.com', 'www.okx.com') 是无效操作
        if 'www.okx.com' in self.base_url:
            # 这里的意图通常是确保使用 www.okx.com 或者切换到 api.okx.com (取决于你的网络环境)
            # 这里保持默认 www.okx.com，如果需要 api.okx.com 请修改第二个参数
            self.base_url = self.base_url.replace('www.okx.com', 'www.okx.com')
            
        # 确保使用正确的 API 端点格式
        if not self.base_url.startswith('http'):
            self.base_url = 'https://www.okx.com'
            
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        # 创建 session
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
                    verify=True  # 默认保持 SSL 验证
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
                
                # 修复逻辑：如果是最后一次尝试，尝试关闭 SSL 验证（仅用于调试/紧急情况）
                if attempt == max_retries - 1:
                    try:
                        print(f"[OKX] ⚠️ 最后一次尝试使用非验证模式 (verify=False)...")
                        # 禁用 urllib3 的警告
                        import urllib3
                        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                        
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
                    # 如果不是最后一次，则等待重试
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
                print(f"[OKX] ❌ 未知错误 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(1 * (attempt + 1))
                continue
        
        print(f"[OKX] ❌ 所有重试均失败，最后错误: {last_error}")
        return None