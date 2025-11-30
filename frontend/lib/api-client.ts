/**
 * API 客户端 - 直接调用后端 API
 * 用于在服务端组件或 API 路由中使用
 */
import { API_ENDPOINTS, apiFetch } from "./api-config"
import type {
  TradesResponse,
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
 * 删除交易单
 */
export async function deleteTrade(tradeId: number): Promise<{ success: boolean; message?: string }> {
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"
  const url = `/api/trades/${tradeId}`
  
  const token = typeof window !== "undefined" ? localStorage.getItem("auth_token") : null
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  }
  
  if (token) {
    headers["Authorization"] = `Bearer ${token}`
  }
  
  const response = await fetch(url, {
    method: "DELETE",
    headers,
  })
  
  if (response.status === 401) {
    if (typeof window !== "undefined") {
      localStorage.removeItem("auth_token")
      window.location.href = "/login"
    }
    throw new Error("未授权，请重新登录")
  }
  
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new Error(errorData.error || errorData.message || `HTTP ${response.status}: ${response.statusText}`)
  }
  
  const data = await response.json()
  return data
}

