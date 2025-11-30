"use client"

import { useMemo, useEffect } from "react"
import { useRouter } from "next/navigation"
import { useTrades, useTraders } from "@/hooks/use-trades"
import { useAuth } from "@/hooks/use-auth"
import { TraderOverviewCard } from "@/components/trader-overview-card"
import { PriceTicker } from "@/components/price-ticker"
import { Skeleton } from "@/components/ui/skeleton"
import { Button } from "@/components/ui/button"
import type { Trader } from "@/lib/types"
import { Activity, Settings, LogOut, RefreshCw } from "lucide-react"
import { cn } from "@/lib/utils"
import Link from "next/link"

export default function TradingDashboard() {
  const router = useRouter()
  const { isAuthenticated, logout } = useAuth()
  const { traders, isLoading: tradersLoading, refresh: refreshTraders } = useTraders()
  
  // 获取所有交易数据（不指定channel_id，获取所有）
  const { trades: allTrades, isLoading: tradesLoading, refresh: refreshTrades } = useTrades()

  useEffect(() => {
    if (!isAuthenticated) {
      router.push("/login")
    }
  }, [isAuthenticated, router])

  // 按带单员分组交易
  const tradesByTrader = useMemo(() => {
    const grouped: Record<string, typeof allTrades> = {}
    traders.forEach(trader => {
      grouped[trader.id] = allTrades.filter(t => t.channel_id === trader.channel_id)
    })
    return grouped
  }, [traders, allTrades])

  const handleRefresh = () => {
    refreshTraders()
    refreshTrades()
  }

  return (
    <div className="min-h-screen bg-background">
      {/* 头部 */}
      <header className="border-b border-border bg-card/50 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Activity className="w-5 h-5 text-primary" />
              <h1 className="text-lg font-semibold">交易监控面板</h1>
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
        {/* 标题和刷新按钮 */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold">交易监控概览</h2>
            <p className="text-sm text-muted-foreground mt-1">查看所有带单员的交易情况</p>
          </div>
          <Button variant="outline" size="sm" onClick={handleRefresh} disabled={tradersLoading || tradesLoading}>
            <RefreshCw className={cn("w-4 h-4 mr-2", (tradersLoading || tradesLoading) && "animate-spin")} />
            刷新
          </Button>
        </div>

        {/* 带单员交易概览卡片 */}
        {tradersLoading || tradesLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <Skeleton key={i} className="h-64 rounded-lg" />
            ))}
          </div>
        ) : traders.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-muted-foreground">暂无带单员数据</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {traders.map((trader) => (
              <TraderOverviewCard 
                key={trader.id} 
                trader={trader} 
                trades={tradesByTrader[trader.id] || []} 
              />
            ))}
          </div>
        )}
      </main>
    </div>
  )
}
