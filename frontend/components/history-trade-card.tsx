"use client"

import { Card, CardContent } from "@/components/ui/card"
import { StatusBadge } from "./status-badge"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { formatPrice, formatPnL, formatPercent } from "@/lib/trade-utils"
import type { Trade } from "@/lib/types"
import { ChevronDown, ChevronUp, Trash2 } from "lucide-react"
import { useState } from "react"
import { deleteTrade } from "@/lib/api-client"
import { useAuth } from "@/hooks/use-auth"
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

interface HistoryTradeCardProps {
  trade: Trade
  onDelete?: (tradeId: number) => void
}

export function HistoryTradeCard({ trade, onDelete }: HistoryTradeCardProps) {
  const { isAdmin } = useAuth()
  const [expanded, setExpanded] = useState(false)
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const isLong = trade.side === "long"
  const isProfitable = trade.pnl_points >= 0
  
  // 已结束的交易，使用固定的盈亏数据，不再实时计算
  const ENDED_STATUSES = ["已止盈", "已止损", "带单主动止盈", "带单主动止损"]
  const isEnded = ENDED_STATUSES.includes(trade.status)
  
  // 如果交易已结束，使用固定的pnl_points和pnl_percent，不再使用current_price计算
  const finalPnlPoints = isEnded ? (trade.pnl_points ?? 0) : trade.pnl_points ?? 0
  const finalPnlPercent = isEnded ? (trade.pnl_percent ?? 0) : trade.pnl_percent ?? 0

  const handleDelete = async () => {
    setIsDeleting(true)
    try {
      await deleteTrade(trade.id)
      setShowDeleteDialog(false)
      if (onDelete) {
        onDelete(trade.id)
      }
    } catch (error) {
      console.error("删除交易单失败:", error)
      alert(error instanceof Error ? error.message : "删除失败")
    } finally {
      setIsDeleting(false)
    }
  }

  return (
    <Card className="bg-card/50 border-border/50">
      <CardContent className="p-3">
        {/* 折叠的摘要行 */}
        <div className="flex items-center gap-2">
          <button onClick={() => setExpanded(!expanded)} className="flex-1 flex items-center justify-between gap-4">
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
              <span className={cn("font-mono text-sm font-medium", finalPnlPoints >= 0 ? "text-profit" : "text-loss")}>
                {formatPnL(finalPnlPoints)}
            </span>
            <span className="text-xs text-muted-foreground">{trade.created_at_str}</span>
            {expanded ? (
              <ChevronUp className="w-4 h-4 text-muted-foreground" />
            ) : (
              <ChevronDown className="w-4 h-4 text-muted-foreground" />
            )}
          </div>
        </button>
          {/* 删除按钮 - 在折叠状态下也可见（仅管理员） */}
          {isAdmin && (
            <Button
              variant="ghost"
              size="icon"
              onClick={(e) => {
                e.stopPropagation()
                setShowDeleteDialog(true)
              }}
              className="h-8 w-8 text-destructive hover:text-destructive hover:bg-destructive/10"
            >
              <Trash2 className="w-4 h-4" />
            </Button>
          )}
        </div>

        {/* 展开的详情 */}
        {expanded && (
          <div className="mt-3 pt-3 border-t border-border/50 space-y-3">
            {/* 删除按钮（仅管理员） */}
            {isAdmin && (
              <div className="flex justify-end">
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation()
                    setShowDeleteDialog(true)
                  }}
                  className="gap-2"
                >
                  <Trash2 className="w-4 h-4" />
                  删除
                </Button>
              </div>
            )}
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
                <p className={cn("font-mono", finalPnlPercent >= 0 ? "text-profit" : "text-loss")}>
                  {formatPercent(finalPnlPercent)}
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

        {/* 删除确认对话框 */}
        <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>确认删除</AlertDialogTitle>
              <AlertDialogDescription>
                确定要删除这笔交易记录吗？此操作无法撤销。
                <br />
                <span className="font-medium">{trade.symbol} - {trade.side === "long" ? "多" : "空"}</span>
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel disabled={isDeleting}>取消</AlertDialogCancel>
              <AlertDialogAction
                onClick={handleDelete}
                disabled={isDeleting}
                className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              >
                {isDeleting ? "删除中..." : "删除"}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </CardContent>
    </Card>
  )
}
