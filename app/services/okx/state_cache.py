import threading
import time
from typing import Dict, Set
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
        # 动态跟踪的币种列表（除了BTC和ETH）
        self._tracked_symbols: Set[str] = set()
        self._symbols_lock = threading.Lock()

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop = False
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop = True

    def add_symbol(self, symbol: str):
        """动态添加需要跟踪的币种（排除BTC和ETH）"""
        # 检查是否是BTC或ETH
        if self._is_btc_or_eth(symbol):
            return  # BTC和ETH已经在配置中，不需要单独添加
        
        with self._symbols_lock:
            if symbol not in self._tracked_symbols:
                self._tracked_symbols.add(symbol)
                print(f'[OKX] ✅ 添加新币种到价格跟踪列表: {symbol}')
    
    def _is_btc_or_eth(self, symbol: str) -> bool:
        """检查币种是否是BTC或ETH"""
        symbol_upper = symbol.upper()
        return 'BTC' in symbol_upper or 'ETH' in symbol_upper
    
    def _get_all_symbols(self) -> list:
        """获取所有需要跟踪的币种（配置的 + 动态添加的）"""
        # 基础币种（从配置中获取，通常是BTC和ETH）
        base_symbols = self.settings.OKX_INST_IDS or []
        
        # 动态添加的币种
        with self._symbols_lock:
            dynamic_symbols = list(self._tracked_symbols)
        
        # 合并并去重
        all_symbols = list(set(base_symbols + dynamic_symbols))
        return all_symbols

    def _run(self):
        interval = max(5.0, float(self.settings.OKX_POLL_INTERVAL_SEC))
        print(f'[OKX] ✅ 价格轮询已启动 - 间隔: {interval}秒')
        consecutive_errors = 0
        max_consecutive_errors = 10  # 连续10次错误后降低频率
        
        while not self._stop:
            try:
                # 获取所有需要跟踪的币种（配置的 + 动态添加的）
                inst_ids = self._get_all_symbols()
                success_count = 0
                for inst in inst_ids:
                    try:
                        res = self.client.request("GET", "/api/v5/market/ticker", {"instId": inst}, timeout=8)
                        if res and res.get('code') == '0' and res.get('data'):
                            t = res['data'][0]
                            try:
                                new_price = float(t['last'])
                                self.prices[inst] = new_price
                                success_count += 1
                                consecutive_errors = 0  # 重置错误计数
                            except Exception as e:
                                print(f'[OKX] ⚠️ 价格解析失败 - {inst}: {e}')
                        elif res:
                            print(f'[OKX] ⚠️ API返回错误 - {inst}: code={res.get("code")}, msg={res.get("msg")}')
                    except Exception as e:
                        print(f'[OKX] ⚠️ 获取 {inst} 价格失败: {e}')
                        consecutive_errors += 1
                
                # 如果所有请求都失败，增加错误计数
                if success_count == 0 and inst_ids:
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        # 降低轮询频率
                        interval = min(interval * 2, 60.0)
                        print(f'[OKX] ⚠️ 连续 {consecutive_errors} 次失败，降低轮询频率至 {interval} 秒')
                        consecutive_errors = 0  # 重置计数
                elif success_count > 0:
                    consecutive_errors = 0  # 重置错误计数
                    # 恢复正常频率
                    original_interval = max(5.0, float(self.settings.OKX_POLL_INTERVAL_SEC))
                    if interval > original_interval:
                        interval = original_interval
                        print(f'[OKX] ✅ 恢复正常轮询频率: {interval} 秒')
            except Exception as e:
                print(f'[OKX] ❌ 轮询异常: {e}')
                consecutive_errors += 1
            time.sleep(interval)

    def get_price(self, inst_id: str) -> float:
        """获取指定币种的实时价格"""
        return self.prices.get(inst_id)
    
    def get_all_prices(self) -> Dict[str, float]:
        """获取所有已缓存的价格"""
        return self.prices.copy()
