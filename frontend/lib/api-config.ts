/**
 * API 配置
 * 后端 API 基础地址
 * 如果后端运行在本地，默认是 http://localhost:8000
 * 可以通过环境变量 NEXT_PUBLIC_API_BASE_URL 覆盖
 */
export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"

/**
 * API 端点
 */
export const API_ENDPOINTS = {
  trades: `${API_BASE_URL}/api/trades`,
  tradeDetail: (id: number) => `${API_BASE_URL}/api/trades/${id}`,
  prices: `${API_BASE_URL}/api/prices`,
  traders: `${API_BASE_URL}/api/traders`,
  channelStatus: `${API_BASE_URL}/api/channels/status`,
} as const

/**
 * 创建带错误处理的 fetch 请求
 */
export async function apiFetch<T>(
  url: string,
  options?: RequestInit
): Promise<T> {
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
    })

    if (!response.ok) {
      // 处理 HTTP 错误
      const errorText = await response.text()
      let errorMessage = `HTTP ${response.status}: ${response.statusText}`
      
      try {
        const errorJson = JSON.parse(errorText)
        errorMessage = errorJson.message || errorJson.error || errorMessage
      } catch {
        // 如果不是 JSON，使用原始文本
        if (errorText) errorMessage = errorText
      }

      throw new Error(errorMessage)
    }

    const data = await response.json()
    return data as T
  } catch (error) {
    // 网络错误或其他错误
    if (error instanceof Error) {
      throw error
    }
    throw new Error("未知错误")
  }
}

