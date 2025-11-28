"use client"

import { Card, CardContent } from "@/components/ui/card"
import type { Trade } from "@/lib/types"
import { TrendingUp, TrendingDown, Clock, CheckCircle } from "lucide-react"

interface StatsSummaryProps {
  trades: Trade[]
}

export function StatsSummary({ trades }: StatsSummaryProps) {
  const stats = {
    total: trades.length,
    profit: trades.filter((t) => t.status === "浮盈").length,
    loss: trades.filter((t) => t.status === "浮亏").length,
    closed: trades.filter((t) => ["已止盈", "已止损", "带单主动止盈", "带单主动止损"].includes(t.status)).length,
    pending: trades.filter((t) => t.status === "未进场").length,
  }

  const totalPnL = trades.reduce((sum, t) => sum + t.pnl_points, 0)

  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
      <Card className="bg-card">
        <CardContent className="p-4">
          <div className="flex items-center gap-2 text-muted-foreground text-sm mb-1">
            <CheckCircle className="w-4 h-4" />
            总交易
          </div>
          <p className="text-2xl font-bold">{stats.total}</p>
        </CardContent>
      </Card>

      <Card className="bg-card">
        <CardContent className="p-4">
          <div className="flex items-center gap-2 text-profit text-sm mb-1">
            <TrendingUp className="w-4 h-4" />
            浮盈中
          </div>
          <p className="text-2xl font-bold text-profit">{stats.profit}</p>
        </CardContent>
      </Card>

      <Card className="bg-card">
        <CardContent className="p-4">
          <div className="flex items-center gap-2 text-loss text-sm mb-1">
            <TrendingDown className="w-4 h-4" />
            浮亏中
          </div>
          <p className="text-2xl font-bold text-loss">{stats.loss}</p>
        </CardContent>
      </Card>

      <Card className="bg-card">
        <CardContent className="p-4">
          <div className="flex items-center gap-2 text-muted-foreground text-sm mb-1">
            <Clock className="w-4 h-4" />
            已结束
          </div>
          <p className="text-2xl font-bold">{stats.closed}</p>
        </CardContent>
      </Card>

      <Card className="bg-card">
        <CardContent className="p-4">
          <div className="text-muted-foreground text-sm mb-1">总盈亏</div>
          <p className={`text-2xl font-bold font-mono ${totalPnL >= 0 ? "text-profit" : "text-loss"}`}>
            {totalPnL >= 0 ? "+" : ""}
            {totalPnL.toFixed(2)}
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
