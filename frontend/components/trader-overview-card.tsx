"use client"

import { Card, CardContent } from "@/components/ui/card"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { cn } from "@/lib/utils"
import type { Trader, Trade, TradeStatus } from "@/lib/types"
import { TrendingUp, TrendingDown, Clock, ArrowRight } from "lucide-react"
import { formatPnL, formatPercent } from "@/lib/trade-utils"
import { useRouter } from "next/navigation"

interface TraderOverviewCardProps {
  trader: Trader
  trades: Trade[]
}

const ENDED_STATUSES: TradeStatus[] = ["已止盈", "已止损", "带单主动止盈", "带单主动止损"]

export function TraderOverviewCard({ trader, trades }: TraderOverviewCardProps) {
  const router = useRouter()
  
  // 计算统计数据
  const activeTrades = trades.filter(t => !ENDED_STATUSES.includes(t.status))
  const pendingTrades = trades.filter(t => t.status === "待入场")
  const endedTrades = trades.filter(t => ENDED_STATUSES.includes(t.status))
  
  // 计算总盈亏（只计算已入场的交易）
  const enteredTrades = activeTrades.filter(t => t.status !== "待入场")
  const totalPnl = enteredTrades.reduce((sum, t) => {
    if (t.pnl_points !== null && t.pnl_points !== undefined) {
      return sum + t.pnl_points
    }
    return sum
  }, 0)
  
  const totalPnlPercent = enteredTrades.length > 0 
    ? enteredTrades.reduce((sum, t) => {
        if (t.pnl_percent !== null && t.pnl_percent !== undefined) {
          return sum + t.pnl_percent
        }
        return sum
      }, 0) / enteredTrades.length
    : 0
  
  // 计算盈利和亏损交易数
  const profitableTrades = enteredTrades.filter(t => (t.pnl_points ?? 0) >= 0).length
  const losingTrades = enteredTrades.filter(t => (t.pnl_points ?? 0) < 0).length
  
  const handleClick = () => {
    router.push(`/trader/${trader.id}`)
  }

  return (
    <Card
      className={cn(
        "cursor-pointer transition-all duration-200 hover:shadow-lg hover:shadow-black/20 border-l-4",
        totalPnl >= 0 ? "border-l-profit" : "border-l-loss",
        "bg-card"
      )}
      onClick={handleClick}
    >
      <CardContent className="p-5 space-y-4">
        {/* 头部：带单员信息 */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Avatar className="w-12 h-12">
              <AvatarImage src={trader.avatar || "/placeholder.svg"} alt={trader.name} />
              <AvatarFallback className="bg-primary/20 text-primary font-semibold">
                {trader.name.slice(0, 2)}
              </AvatarFallback>
            </Avatar>
            <div>
              <h3 className="font-semibold text-lg">{trader.name}</h3>
              <p className="text-sm text-muted-foreground">{trader.channel_name}</p>
            </div>
          </div>
          <ArrowRight className="w-5 h-5 text-muted-foreground" />
        </div>

        {/* 总盈亏 */}
        <div className="bg-muted/50 rounded-lg p-4 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">总盈亏</span>
            <span className={cn(
              "font-mono text-2xl font-bold",
              totalPnl >= 0 ? "text-profit" : "text-loss"
            )}>
              {formatPnL(totalPnl)}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">平均盈亏比例</span>
            <span className={cn(
              "font-mono text-sm font-medium",
              totalPnlPercent >= 0 ? "text-profit" : "text-loss"
            )}>
              {formatPercent(totalPnlPercent)}
            </span>
          </div>
        </div>

        {/* 交易统计 */}
        <div className="grid grid-cols-3 gap-3 text-center">
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">活跃单</p>
            <p className="text-lg font-semibold">{activeTrades.length}</p>
          </div>
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">待入场</p>
            <p className="text-lg font-semibold text-muted-foreground">{pendingTrades.length}</p>
          </div>
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">已结束</p>
            <p className="text-lg font-semibold">{endedTrades.length}</p>
          </div>
        </div>

        {/* 盈亏统计 */}
        {enteredTrades.length > 0 && (
          <div className="flex items-center justify-between pt-2 border-t border-border">
            <div className="flex items-center gap-4 text-sm">
              <div className="flex items-center gap-1.5">
                <TrendingUp className="w-4 h-4 text-profit" />
                <span className="text-muted-foreground">盈利:</span>
                <span className="font-medium text-profit">{profitableTrades}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <TrendingDown className="w-4 h-4 text-loss" />
                <span className="text-muted-foreground">亏损:</span>
                <span className="font-medium text-loss">{losingTrades}</span>
              </div>
            </div>
          </div>
        )}

        {/* 最新交易预览 */}
        {activeTrades.length > 0 && (
          <div className="pt-2 border-t border-border space-y-2">
            <p className="text-xs text-muted-foreground mb-2">最新交易</p>
            {activeTrades.slice(0, 3).map((trade) => (
              <div key={trade.id} className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  <span className="font-medium">{trade.symbol}</span>
                  <span className={cn(
                    "px-1.5 py-0.5 rounded text-xs",
                    trade.side === "long" ? "bg-profit/20 text-profit" : "bg-loss/20 text-loss"
                  )}>
                    {trade.side === "long" ? "多" : "空"}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  {trade.status === "待入场" ? (
                    <span className="text-xs text-muted-foreground">待入场</span>
                  ) : (
                    <span className={cn(
                      "font-mono text-xs",
                      (trade.pnl_points ?? 0) >= 0 ? "text-profit" : "text-loss"
                    )}>
                      {formatPnL(trade.pnl_points ?? 0)}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

