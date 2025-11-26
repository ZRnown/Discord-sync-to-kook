from typing import List
from datetime import datetime
from .client import OKXClient

class OKXCopyTrading:
    def __init__(self):
        self.client = OKXClient()

    def get_lead_traders_rank(self, limit: int = 5) -> List[str]:
        endpoint = "/api/v5/copytrading/public-lead-traders"
        params = {"instType": "SWAP", "sortType": "pnl", "limit": limit}
        res = self.client.request("GET", endpoint, params)
        traders = []
        if res and res.get('code') == '0':
            for rank_data in res['data']:
                for trader in rank_data['ranks']:
                    traders.append(trader['uniqueCode'])
        return traders

    def get_current_positions(self, unique_code: str):
        endpoint = "/api/v5/copytrading/public-current-subpositions"
        params = {"uniqueCode": unique_code, "instType": "SWAP"}
        res = self.client.request("GET", endpoint, params)
        data = []
        if res and res.get('code') == '0':
            data = res['data']
        return data

    def get_position_history(self, unique_code: str, limit: int = 5):
        endpoint = "/api/v5/copytrading/public-subpositions-history"
        params = {"uniqueCode": unique_code, "instType": "SWAP", "limit": limit}
        res = self.client.request("GET", endpoint, params)
        data = []
        if res and res.get('code') == '0':
            data = res['data']
        return data
