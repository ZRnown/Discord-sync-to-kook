"""
带单员配置管理类
用于管理带单员与 Discord 频道的映射关系
"""
from typing import Dict, List, Optional
from app.config.settings import get_settings


class TraderConfig:
    """带单员配置管理类"""
    
    def __init__(self):
        self.reload_config()
    
    def reload_config(self):
        """重新加载配置"""
        self.settings = get_settings()
        self.trader_map = self.settings.TRADER_CONFIG
    
    def get_trader_by_id(self, trader_id: str) -> Optional[Dict]:
        """根据带单员ID获取配置"""
        return self.trader_map.get(trader_id)
    
    def get_trader_by_channel_id(self, channel_id: str) -> Optional[Dict]:
        """根据频道ID获取带单员配置"""
        for trader in self.trader_map.values():
            if trader.get('channel_id') == channel_id:
                return trader
        return None
    
    def get_all_traders(self) -> List[Dict]:
        """获取所有带单员配置"""
        return list(self.trader_map.values())
    
    def get_channel_id(self, trader_id: str) -> Optional[str]:
        """获取带单员对应的频道ID"""
        trader = self.get_trader_by_id(trader_id)
        return trader.get('channel_id') if trader else None
    
    def get_trader_name(self, trader_id: str) -> Optional[str]:
        """获取带单员名称"""
        trader = self.get_trader_by_id(trader_id)
        return trader.get('name') if trader else None
    
    def is_trader_configured(self, trader_id: str) -> bool:
        """检查带单员是否已配置"""
        return trader_id in self.trader_map
    
    def is_channel_monitored(self, channel_id: str) -> bool:
        """检查频道是否被监控（是否有对应的带单员配置）"""
        return self.get_trader_by_channel_id(channel_id) is not None

