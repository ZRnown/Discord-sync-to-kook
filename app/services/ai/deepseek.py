import requests
from typing import Optional, Dict
from app.config.settings import get_settings

class DeepseekClient:
    def __init__(self):
        self.settings = get_settings()
        self.api_key = self.settings.DEEPSEEK_API_KEY
        self.endpoint = self.settings.DEEPSEEK_ENDPOINT
        self.model = self.settings.DEEPSEEK_MODEL

    def available(self) -> bool:
        return bool(self.api_key)

    def extract_trade(self, text: str) -> Optional[Dict]:
        if not self.available():
            return None
        prompt = (
            "你是交易文本解析助手。请从中文交易信号或战报中提取结构化字段，"
            "如果是入场信号，输出: {type:'entry', symbol, side: 'long'|'short', entry_price, take_profit, stop_loss}. "
            "如果是出场/止盈/止损/全部出局更新，输出: {type:'update', status, pnl_points?, text}. "
            "仅返回JSON，无多余文本。若无法提取，返回 {}。"
        )
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": text},
            ]
        }
        try:
            headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
            r = requests.post(self.endpoint, json=body, headers=headers, timeout=15)
            if r.status_code == 200:
                data = r.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "{}")
                import json
                return json.loads(content)
            else:
                print(f"Deepseek失败: {r.status_code} {r.text}")
                return None
        except Exception as e:
            print(f"Deepseek异常: {e}")
            return None
