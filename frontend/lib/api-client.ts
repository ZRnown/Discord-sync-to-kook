/**
 * API 客户端 - 直接调用后端 API
 * 用于在服务端组件或 API 路由中使用
 */
import { API_ENDPOINTS, apiFetch } from "./api-config"
import type {
  TradesResponse,
  TradeDetailResponse,
  PricesResponse,
  TradersResponse,
} from "./types"

/**
 * 获取交易单列表
 */
export async function getTrades(channelId?: string): Promise<TradesResponse> {
  const url = channelId
    ? `${API_ENDPOINTS.trades}?channel_id=${channelId}`
    : API_ENDPOINTS.trades
  return apiFetch<TradesResponse>(url)
}

/**
 * 获取单个交易单详情
 */
export async function getTradeDetail(id: number): Promise<TradeDetailResponse> {
  return apiFetch<TradeDetailResponse>(API_ENDPOINTS.tradeDetail(id))
}

/**
 * 获取实时价格
 */
export async function getPrices(): Promise<PricesResponse> {
  return apiFetch<PricesResponse>(API_ENDPOINTS.prices)
}

/**
 * 获取交易员列表
 */
export async function getTraders(): Promise<TradersResponse> {
  return apiFetch<TradersResponse>(API_ENDPOINTS.traders)
}

/**
 * 获取频道状态
 */
export async function getChannelStatus() {
  return apiFetch(API_ENDPOINTS.channelStatus)
}

