from .client import OKXClient

def get_market_price(inst_id: str):
    client = OKXClient()
    res = client.request("GET", "/api/v5/market/ticker", {"instId": inst_id})
    if res and res.get('code') == '0':
        t = res['data'][0]
        return {"instId": t['instId'], "last": t['last'], "askPx": t['askPx'], "bidPx": t['bidPx'], "ts": t['ts']}
    return None
