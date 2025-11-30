"use client"

import { useRef, useEffect, useState } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { StatusBadge } from "./status-badge"
import { PriceProgressBar } from "./price-progress-bar"
import { cn } from "@/lib/utils"
import { formatPrice, formatPnL, formatPercent, getStatusBorderColor } from "@/lib/trade-utils"
import type { Trade } from "@/lib/types"
import { TrendingUp, TrendingDown, Clock, X } from "lucide-react"
import { closeTrade } from "@/lib/api-client"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"

interface TradeCardProps {
  trade: Trade
  onClose?: () => void
}

export function TradeCard({ trade, onClose }: TradeCardProps) {
  const prevPriceRef = useRef(trade.current_price)
  const [priceAnimation, setPriceAnimation] = useState<"up" | "down" | null>(null)
  const [showCloseDialog, setShowCloseDialog] = useState(false)
  const [isClosing, setIsClosing] = useState(false)

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
  
  // 检查是否已结束
  const ENDED_STATUSES = ["已止盈", "已止损", "带单主动止盈", "带单主动止损"]
  const isEnded = ENDED_STATUSES.includes(trade.status)

  const handleClose = async () => {
    setIsClosing(true)
    try {
      await closeTrade(trade.id)
      setShowCloseDialog(false)
      if (onClose) {
        onClose()
      }
    } catch (error) {
      console.error("手动结单失败:", error)
      alert(error instanceof Error ? error.message : "手动结单失败")
    } finally {
      setIsClosing(false)
    }
  }

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

        {/* 部分出局时显示已出局和剩余部分的盈亏 */}
        {(trade.status.includes("部分") || trade.status.includes("部分出局")) && 
         trade.exited_pnl_points !== undefined && trade.remaining_pnl_points !== undefined && (
          <div className="bg-muted/30 rounded-lg px-3 py-2 space-y-1.5">
            <p className="text-xs font-medium text-muted-foreground mb-1">部分出局详情</p>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <p className="text-[10px] text-muted-foreground mb-0.5">已出局盈亏</p>
                <p className={cn("font-mono text-sm font-semibold", trade.exited_pnl_points >= 0 ? "text-profit" : "text-loss")}>
                  {formatPnL(trade.exited_pnl_points)}
                </p>
              </div>
              <div className="text-right">
                <p className="text-[10px] text-muted-foreground mb-0.5">剩余部分盈亏</p>
                <p className={cn("font-mono text-sm font-semibold", trade.remaining_pnl_points >= 0 ? "text-profit" : "text-loss")}>
                  {formatPnL(trade.remaining_pnl_points)}
                </p>
              </div>
            </div>
          </div>
        )}

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

        {/* 底部：时间和操作按钮 */}
        <div className="flex items-center justify-between text-xs text-muted-foreground pt-2 border-t border-border">
          <div className="flex items-center">
          <Clock className="w-3 h-3 mr-1" />
          <span>{trade.created_at_str}</span>
          </div>
          {!isEnded && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowCloseDialog(true)}
              className="h-7 text-xs gap-1.5"
            >
              <X className="w-3 h-3" />
              手动结单
            </Button>
          )}
        </div>
      </CardContent>

      {/* 手动结单确认对话框 */}
      <AlertDialog open={showCloseDialog} onOpenChange={setShowCloseDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认手动结单</AlertDialogTitle>
            <AlertDialogDescription>
              确定要手动结单吗？系统将根据当前价格计算盈亏并标记为
              {isProfitable ? "带单主动止盈" : "带单主动止损"}。
              <br />
              <span className="font-medium">{trade.symbol} - {trade.side === "long" ? "多" : "空"}</span>
              <br />
              <span className="text-sm text-muted-foreground">
                当前价格: {formatPrice(trade.current_price, trade.symbol)}
              </span>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isClosing}>取消</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleClose}
              disabled={isClosing}
              className="bg-primary text-primary-foreground hover:bg-primary/90"
            >
              {isClosing ? "结单中..." : "确认结单"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Card>
  )
}
