import requests
from typing import Optional, Dict
from app.config.settings import get_settings

class OKXClient:
    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.OKX_REST_BASE.rstrip('/')
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0"
        }

    def request(self, method: str, endpoint: str, params: Optional[Dict] = None, timeout: int = 10):
        url = self.base_url + endpoint
        try:
            resp = requests.request(method, url, params=params, headers=self.headers, timeout=timeout)
            if resp.status_code == 200:
                return resp.json()
            else:
                print(f"请求失败: {resp.status_code}, {resp.text}")
                return None
        except Exception as e:
            print(f"网络错误: {e}")
            return None
