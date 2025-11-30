"use client"

import useSWR from "swr"
import type { TradesResponse, TradersResponse, PricesResponse } from "@/lib/types"

const fetcher = async (url: string) => {
  const token = typeof window !== "undefined" ? localStorage.getItem("auth_token") : null
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  }
  
  if (token) {
    headers["Authorization"] = `Bearer ${token}`
  }
  
  const res = await fetch(url, { headers })
  
  if (res.status === 401) {
    // 未授权，清除token并跳转到登录页
    if (typeof window !== "undefined") {
      localStorage.removeItem("auth_token")
      window.location.href = "/login"
    }
    const errorData = await res.json().catch(() => ({}))
    throw new Error(errorData.error || "未授权，请重新登录")
  }
  
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}))
    const errorMessage = errorData.error || errorData.message || `HTTP ${res.status}: ${res.statusText}`
    throw new Error(errorMessage)
  }
  const data = await res.json()
  
  // 检查响应格式
  if (!data.success) {
    throw new Error(data.error || data.message || "请求失败")
  }
  
  return data
}

export function useTrades(channelId?: string) {
  const url = channelId ? `/api/trades?channel_id=${channelId}` : "/api/trades"
  const { data, error, isLoading, mutate } = useSWR<TradesResponse>(
    url,
    fetcher,
    {
    refreshInterval: 3000,
    revalidateOnFocus: true,
      revalidateOnReconnect: true,
      errorRetryCount: 3,
      errorRetryInterval: 2000,
      onError: (err) => {
        console.error("获取交易单失败:", err)
      },
    }
  )

  return {
    trades: data?.data || [],
    isLoading,
    isError: !!error,
    error: error?.message,
    refresh: mutate,
  }
}

export function useTraders() {
  const { data, error, isLoading, mutate } = useSWR<TradersResponse>("/api/traders", fetcher, {
    revalidateOnFocus: true,
    revalidateOnReconnect: true,
    errorRetryCount: 3,
    onError: (err) => {
      console.error("获取交易员列表失败:", err)
    },
  })

  return {
    traders: data?.data || [],
    isLoading,
    isError: !!error,
    error: error?.message,
    refresh: mutate,
  }
}

export function usePrices() {
  const { data, error, isLoading } = useSWR<PricesResponse>("/api/prices", fetcher, {
    refreshInterval: 3000,
    revalidateOnFocus: true,
    revalidateOnReconnect: true,
    errorRetryCount: 3,
    errorRetryInterval: 2000,
    onError: (err) => {
      console.error("获取价格失败:", err)
    },
  })

  return {
    prices: data?.data || {},
    isLoading,
    isError: !!error,
    error: error?.message,
  }
}
