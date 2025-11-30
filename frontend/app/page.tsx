"use client"

import { useState, useMemo, useEffect } from "react"
import { useRouter } from "next/navigation"
import { useTrades, useTraders } from "@/hooks/use-trades"
import { useAuth } from "@/hooks/use-auth"
import { TradeCard } from "@/components/trade-card"
import { FilterBar } from "@/components/filter-bar"
import { TraderSelector } from "@/components/trader-selector"
import { PriceTicker } from "@/components/price-ticker"
import { StatsSummary } from "@/components/stats-summary"
import { HistorySection } from "@/components/history-section"
import { Skeleton } from "@/components/ui/skeleton"
import { Button } from "@/components/ui/button"
import type { StatusFilter, SideFilter, Trader, TradeStatus } from "@/lib/types"
import { Activity, ArrowLeft, Settings, LogOut } from "lucide-react"
import Link from "next/link"

const ENDED_STATUSES: TradeStatus[] = ["已止盈", "已止损", "带单主动止盈", "带单主动止损"]

export default function TradingDashboard() {
  const router = useRouter()
  const { isAuthenticated, logout } = useAuth()
  const [selectedTrader, setSelectedTrader] = useState<Trader | null>(null)
  const { traders, isLoading: tradersLoading } = useTraders()
  const { trades, isLoading, isError, error, refresh } = useTrades(selectedTrader?.channel_id)

  useEffect(() => {
    if (!isAuthenticated) {
      router.push("/login")
    }
  }, [isAuthenticated, router])

  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all")
  const [sideFilter, setSideFilter] = useState<SideFilter>("all")
  const [symbolFilter, setSymbolFilter] = useState<string>("all")

  const symbols = useMemo(() => {
    return [...new Set(trades.map((t) => t.symbol))]
  }, [trades])

  const { activeTrades, historyTrades } = useMemo(() => {
    const active: typeof trades = []
    const history: typeof trades = []

    trades.forEach((trade) => {
      if (ENDED_STATUSES.includes(trade.status)) {
        history.push(trade)
      } else {
        active.push(trade)
      }
    })

    // 历史单按时间倒序
    history.sort((a, b) => b.created_at - a.created_at)

    return { activeTrades: active, historyTrades: history }
  }, [trades])

  const filteredTrades = useMemo(() => {
    return activeTrades.filter((trade) => {
      if (statusFilter !== "all" && trade.status !== statusFilter) return false
      if (sideFilter !== "all" && trade.side !== sideFilter) return false
      if (symbolFilter !== "all" && trade.symbol !== symbolFilter) return false
      return true
    })
  }, [activeTrades, statusFilter, sideFilter, symbolFilter])

  const handleSelectTrader = (trader: Trader) => {
    setSelectedTrader(trader)
    setStatusFilter("all")
    setSideFilter("all")
    setSymbolFilter("all")
  }

  const handleBack = () => {
    setSelectedTrader(null)
  }

  return (
    <div className="min-h-screen bg-background">
      {/* 头部 */}
      <header className="border-b border-border bg-card/50 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {selectedTrader && (
                <Button variant="ghost" size="icon" onClick={handleBack} className="mr-2">
                  <ArrowLeft className="w-5 h-5" />
                </Button>
              )}
              <Activity className="w-5 h-5 text-primary" />
              <h1 className="text-lg font-semibold">交易监控面板</h1>
              {selectedTrader && <span className="text-sm text-muted-foreground">/ {selectedTrader.name}</span>}
            </div>
            <div className="flex items-center gap-4">
              <PriceTicker />
              <span className="text-xs text-muted-foreground bg-secondary px-2 py-0.5 rounded">实时</span>
              <Link href="/settings">
                <Button variant="ghost" size="icon">
                  <Settings className="w-5 h-5" />
                </Button>
              </Link>
              <Button variant="ghost" size="icon" onClick={logout}>
                <LogOut className="w-5 h-5" />
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6 space-y-6">
        {!selectedTrader ? (
          <TraderSelector
            traders={traders}
            selectedTrader={selectedTrader}
            onSelect={handleSelectTrader}
            isLoading={tradersLoading}
          />
        ) : (
          <>
            {/* 统计摘要 */}
            <StatsSummary trades={trades} />

            {/* 筛选栏 - 只筛选活跃单 */}
            <FilterBar
              statusFilter={statusFilter}
              sideFilter={sideFilter}
              symbolFilter={symbolFilter}
              symbols={symbols}
              onStatusChange={setStatusFilter}
              onSideChange={setSideFilter}
              onSymbolChange={setSymbolFilter}
              onRefresh={refresh}
              isLoading={isLoading}
            />

            {/* 活跃交易列表 */}
            {isError ? (
              <div className="text-center py-12 space-y-2">
                <p className="text-destructive font-medium">加载失败</p>
                <p className="text-sm text-muted-foreground">
                  {error || "无法连接到后端服务器，请检查 API 配置"}
                </p>
                <Button variant="outline" onClick={() => refresh()} className="mt-4">
                  重试
                </Button>
              </div>
            ) : isLoading && trades.length === 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {[...Array(4)].map((_, i) => (
                  <Skeleton key={i} className="h-48 rounded-lg" />
                ))}
              </div>
            ) : filteredTrades.length === 0 ? (
              <div className="text-center py-12">
                <p className="text-muted-foreground">暂无进行中的交易单</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {filteredTrades.map((trade) => (
                  <TradeCard key={trade.id} trade={trade} />
                ))}
              </div>
            )}

            <HistorySection 
              trades={historyTrades} 
              onTradeDelete={(tradeId) => {
                // 删除后刷新数据
                refresh()
              }}
            />
          </>
        )}
      </main>
    </div>
  )
}
