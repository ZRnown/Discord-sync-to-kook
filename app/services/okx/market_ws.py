import json
import threading
import time
from typing import Set
import websocket
from app.config.settings import get_settings

class OKXMarketWS:
    def __init__(self):
        self.settings = get_settings()
        self.url = self.settings.OKX_WS_URL
        # 默认不订阅，直到显式调用 subscribe
        self.subs: Set[str] = set()
        self.ws = None
        self.thread = None
        self._stop = False

    def _on_message(self, ws, message):
        data = json.loads(message)
        if 'event' in data and data['event'] == 'subscribe':
            print(f"订阅成功: {data.get('arg', {}).get('channel')} - {data.get('arg', {}).get('instId')}")
            return
        if 'data' in data:
            for tick in data['data']:
                inst_id = tick['instId']
                last_price = tick['last']
                print(f"WS推送 [{inst_id}] 最新: {last_price}")

    def _on_error(self, ws, error):
        print(f"Websocket 错误: {error}")

    def _on_close(self, ws, code, reason):
        print("Websocket 连接关闭")
        if not self._stop:
            time.sleep(5)
            self.start()

    def _on_open(self, ws):
        print("Websocket 连接建立，发送订阅...")
        args = [{"channel": "tickers", "instId": inst} for inst in self.subs]
        sub_msg = {"op": "subscribe", "args": args}
        ws.send(json.dumps(sub_msg))

    def start(self):
        self._stop = False
        self.ws = websocket.WebSocketApp(
            self.url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
        )
        self.thread = threading.Thread(target=lambda: self.ws.run_forever(ping_interval=20, ping_timeout=10), daemon=True)
        self.thread.start()

    def stop(self):
        self._stop = True
        if self.ws:
            self.ws.close()

    def subscribe(self, inst_id: str):
        self.subs.add(inst_id)
        if self.ws:
            self.ws.send(json.dumps({"op": "subscribe", "args": [{"channel": "tickers", "instId": inst_id}]}))

    def unsubscribe(self, inst_id: str):
        if inst_id in self.subs:
            self.subs.remove(inst_id)
        if self.ws:
            self.ws.send(json.dumps({"op": "unsubscribe", "args": [{"channel": "tickers", "instId": inst_id}]}))
