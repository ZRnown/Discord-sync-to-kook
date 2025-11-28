"use client"

import { useRef, useEffect, useState } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { StatusBadge } from "./status-badge"
import { PriceProgressBar } from "./price-progress-bar"
import { cn } from "@/lib/utils"
import { formatPrice, formatPnL, formatPercent, getStatusBorderColor } from "@/lib/trade-utils"
import type { Trade } from "@/lib/types"
import { TrendingUp, TrendingDown, Clock } from "lucide-react"

interface TradeCardProps {
  trade: Trade
}

export function TradeCard({ trade }: TradeCardProps) {
  const prevPriceRef = useRef(trade.current_price)
  const [priceAnimation, setPriceAnimation] = useState<"up" | "down" | null>(null)

  useEffect(() => {
    if (trade.current_price !== prevPriceRef.current) {
      setPriceAnimation(trade.current_price > prevPriceRef.current ? "up" : "down")
      prevPriceRef.current = trade.current_price
      const timer = setTimeout(() => setPriceAnimation(null), 500)
      return () => clearTimeout(timer)
    }
  }, [trade.current_price])

  const isLong = trade.side === "long"
  const isProfitable = trade.pnl_points >= 0

  return (
    <Card
      className={cn(
        "transition-all duration-200 hover:shadow-lg hover:shadow-black/20 border-l-4",
        getStatusBorderColor(trade.status),
        "bg-card",
      )}
    >
      <CardContent className="p-4 space-y-4">
        {/* 头部：交易对 + 方向 + 状态 */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h3 className="font-semibold text-lg">{trade.symbol}</h3>
            <span
              className={cn(
                "px-2 py-0.5 rounded text-xs font-medium",
                isLong ? "bg-profit/20 text-profit" : "bg-loss/20 text-loss",
              )}
            >
              {isLong ? (
                <span className="flex items-center gap-1">
                  <TrendingUp className="w-3 h-3" />多
                </span>
              ) : (
                <span className="flex items-center gap-1">
                  <TrendingDown className="w-3 h-3" />空
                </span>
              )}
            </span>
          </div>
          <StatusBadge status={trade.status} />
        </div>

        {/* 价格信息 */}
        <div className="grid grid-cols-3 gap-4">
          <div>
            <p className="text-xs text-muted-foreground mb-1">进场价</p>
            <p className="font-mono font-medium">{formatPrice(trade.entry_price, trade.symbol)}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground mb-1">当前价</p>
            <p
              className={cn(
                "font-mono font-medium text-lg transition-colors",
                priceAnimation === "up" && "price-up text-profit",
                priceAnimation === "down" && "price-down text-loss",
              )}
            >
              {formatPrice(trade.current_price, trade.symbol)}
            </p>
          </div>
          <div className="text-right">
            <p className="text-xs text-muted-foreground mb-1">盈亏</p>
            <p className={cn("font-mono font-bold text-lg", isProfitable ? "text-profit" : "text-loss")}>
              {formatPnL(trade.pnl_points)}
            </p>
            <p className={cn("text-xs font-mono", isProfitable ? "text-profit/80" : "text-loss/80")}>
              {formatPercent(trade.pnl_percent)}
            </p>
          </div>
        </div>

        {/* 价格进度条 */}
        <PriceProgressBar
          currentPrice={trade.current_price}
          entryPrice={trade.entry_price}
          takeProfit={trade.take_profit}
          stopLoss={trade.stop_loss}
          side={trade.side}
          symbol={trade.symbol}
        />

        {/* 止盈止损信息 */}
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div className="flex items-center justify-between bg-profit/10 rounded px-3 py-2">
            <span className="text-muted-foreground">止盈</span>
            <span className="font-mono text-profit">{formatPrice(trade.take_profit, trade.symbol)}</span>
          </div>
          <div className="flex items-center justify-between bg-loss/10 rounded px-3 py-2">
            <span className="text-muted-foreground">止损</span>
            <span className="font-mono text-loss">{formatPrice(trade.stop_loss, trade.symbol)}</span>
          </div>
        </div>

        {/* 底部时间 */}
        <div className="flex items-center text-xs text-muted-foreground pt-2 border-t border-border">
          <Clock className="w-3 h-3 mr-1" />
          <span>{trade.created_at_str}</span>
        </div>
      </CardContent>
    </Card>
  )
}
