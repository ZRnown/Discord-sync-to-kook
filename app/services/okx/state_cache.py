import threading
import time
from typing import Dict, List
from app.config.settings import get_settings
from .client import OKXClient
from .copy_trading import OKXCopyTrading

class OKsmtateCache:
    """简单轮询缓存：instId -> last_price, uniqueCode -> current_positions"""
    def __init__(self):
        self.settings = get_settings()
        self.client = OKXClient()
        self.copy = OKXCopyTrading()
        self.prices: Dict[str, float] = {}
        self.positions: Dict[str, List[dict]] = {}
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
        while not self._stop:
            try:
                # 刷新价格
                inst_ids = self.settings.OKX_INST_IDS or []
                for inst in inst_ids:
                    res = self.client.request("GET", "/api/v5/market/ticker", {"instId": inst})
                    if res and res.get('code') == '0' and res.get('data'):
                        t = res['data'][0]
                        try:
                            self.prices[inst] = float(t['last'])
                        except Exception:
                            pass
                # 刷新带单员当前持仓（如配置了绑定，则按绑定 uniqueCode 刷新）
                bindings = self._get_bindings()
                codes = {b['unique_code'] for b in bindings.values()} if bindings else set()
                for code in codes:
                    data = self.copy.get_current_positions(code)
                    self.positions[code] = data or []
            except Exception as e:
                print(f"OKsmtateCache轮询异常: {e}")
            time.sleep(interval)

    def _get_bindings(self):
        return self.settings.MONITOR_BINDINGS or {}

    def get_price(self, inst_id: str) -> float:
        return self.prices.get(inst_id)

    def get_positions(self, unique_code: str) -> List[dict]:
        return self.positions.get(unique_code, [])
