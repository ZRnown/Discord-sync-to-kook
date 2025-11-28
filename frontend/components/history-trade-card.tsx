"use client"

import { Card, CardContent } from "@/components/ui/card"
import { StatusBadge } from "./status-badge"
import { cn } from "@/lib/utils"
import { formatPrice, formatPnL, formatPercent } from "@/lib/trade-utils"
import type { Trade } from "@/lib/types"
import { ChevronDown, ChevronUp } from "lucide-react"
import { useState } from "react"

interface HistoryTradeCardProps {
  trade: Trade
}

export function HistoryTradeCard({ trade }: HistoryTradeCardProps) {
  const [expanded, setExpanded] = useState(false)
  const isLong = trade.side === "long"
  const isProfitable = trade.pnl_points >= 0

  return (
    <Card className="bg-card/50 border-border/50">
      <CardContent className="p-3">
        {/* 折叠的摘要行 */}
        <button onClick={() => setExpanded(!expanded)} className="w-full flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <span className="font-medium text-sm">{trade.symbol}</span>
            <span
              className={cn(
                "px-1.5 py-0.5 rounded text-xs font-medium",
                isLong ? "bg-profit/20 text-profit" : "bg-loss/20 text-loss",
              )}
            >
              {isLong ? "多" : "空"}
            </span>
            <StatusBadge status={trade.status} size="sm" />
          </div>
          <div className="flex items-center gap-4">
            <span className={cn("font-mono text-sm font-medium", isProfitable ? "text-profit" : "text-loss")}>
              {formatPnL(trade.pnl_points)}
            </span>
            <span className="text-xs text-muted-foreground">{trade.created_at_str}</span>
            {expanded ? (
              <ChevronUp className="w-4 h-4 text-muted-foreground" />
            ) : (
              <ChevronDown className="w-4 h-4 text-muted-foreground" />
            )}
          </div>
        </button>

        {/* 展开的详情 */}
        {expanded && (
          <div className="mt-3 pt-3 border-t border-border/50 space-y-3">
            {/* 价格信息 */}
            <div className="grid grid-cols-4 gap-3 text-sm">
              <div>
                <p className="text-xs text-muted-foreground mb-0.5">进场价</p>
                <p className="font-mono">{formatPrice(trade.entry_price, trade.symbol)}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground mb-0.5">止盈</p>
                <p className="font-mono text-profit">{formatPrice(trade.take_profit, trade.symbol)}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground mb-0.5">止损</p>
                <p className="font-mono text-loss">{formatPrice(trade.stop_loss, trade.symbol)}</p>
              </div>
              <div className="text-right">
                <p className="text-xs text-muted-foreground mb-0.5">盈亏比例</p>
                <p className={cn("font-mono", isProfitable ? "text-profit" : "text-loss")}>
                  {formatPercent(trade.pnl_percent)}
                </p>
              </div>
            </div>

            {/* 更新历史 */}
            {trade.updates && trade.updates.length > 0 && (
              <div className="space-y-1.5">
                <p className="text-xs text-muted-foreground">更新历史</p>
                <div className="space-y-1">
                  {trade.updates.map((update) => (
                    <div
                      key={update.id}
                      className="flex items-center justify-between text-xs bg-muted/30 rounded px-2 py-1.5"
                    >
                      <span className="text-muted-foreground">{update.created_at_str}</span>
                      <span>{update.text || update.status}</span>
                      {update.pnl_points !== 0 && (
                        <span className={cn("font-mono", update.pnl_points > 0 ? "text-profit" : "text-loss")}>
                          {formatPnL(update.pnl_points)}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
