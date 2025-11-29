import threading
import time
from typing import Dict
from app.config.settings import get_settings
from .client import OKXClient

class OKXStateCache:
    """简单轮询缓存：instId -> last_price（仅用于获取实时币价）"""
    def __init__(self):
        self.settings = get_settings()
        self.client = OKXClient()
        self.prices: Dict[str, float] = {}
        self._stop = False
        self._thread = None

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop = False
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop = True

    def _run(self):
        interval = max(2.0, float(self.settings.OKX_POLL_INTERVAL_SEC))
        print(f'[OKX] ✅ 价格轮询已启动 - 间隔: {interval}秒, 交易对: {", ".join(self.settings.OKX_INST_IDS or [])}')
        while not self._stop:
            try:
                # 刷新价格（从所有配置的交易对）
                inst_ids = self.settings.OKX_INST_IDS or []
                for inst in inst_ids:
                    res = self.client.request("GET", "/api/v5/market/ticker", {"instId": inst})
                    if res and res.get('code') == '0' and res.get('data'):
                        t = res['data'][0]
                        try:
                            new_price = float(t['last'])
                            self.prices[inst] = new_price
                            # 移除价格更新日志，只在后台静默更新
                        except Exception as e:
                            print(f'[OKX] ⚠️ 价格解析失败 - {inst}: {e}')
                    elif res:
                        print(f'[OKX] ⚠️ API返回错误 - {inst}: code={res.get("code")}, msg={res.get("msg")}')
            except Exception as e:
                print(f'[OKX] ❌ 轮询异常: {e}')
            time.sleep(interval)

    def get_price(self, inst_id: str) -> float:
        """获取指定币种的实时价格"""
        return self.prices.get(inst_id)
