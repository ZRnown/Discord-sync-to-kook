"use client"

import useSWR from "swr"
import type { TradesResponse, TradersResponse, PricesResponse } from "@/lib/types"

const fetcher = async (url: string) => {
  const res = await fetch(url)
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
  const { data, error, isLoading } = useSWR<TradersResponse>("/api/traders", fetcher, {
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
