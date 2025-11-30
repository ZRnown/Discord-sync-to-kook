import { cn } from "@/lib/utils"
import { calculatePricePosition, calculateEntryPosition, formatPrice } from "@/lib/trade-utils"
import type { TradeSide } from "@/lib/types"

interface PriceProgressBarProps {
  currentPrice: number | null | undefined
  entryPrice: number
  takeProfit: number
  stopLoss: number
  side: TradeSide
  symbol: string
}

export function PriceProgressBar({
  currentPrice,
  entryPrice,
  takeProfit,
  stopLoss,
  side,
  symbol,
}: PriceProgressBarProps) {
  // 如果当前价格为 null 或 undefined，使用入场价作为默认值
  const effectivePrice = currentPrice ?? entryPrice
  const currentPosition = calculatePricePosition(effectivePrice, stopLoss, entryPrice, takeProfit, side)
  const entryPosition = calculateEntryPosition(stopLoss, entryPrice, takeProfit, side)

  // 判断当前价格相对于入场价的位置
  const isInProfit = side === "long" ? effectivePrice > entryPrice : effectivePrice < entryPrice

  // 左侧和右侧标签
  const leftLabel = side === "long" ? "止损" : "止盈"
  const rightLabel = side === "long" ? "止盈" : "止损"
  const leftPrice = side === "long" ? stopLoss : takeProfit
  const rightPrice = side === "long" ? takeProfit : stopLoss

  return (
    <div className="w-full space-y-1">
      {/* 价格标签 */}
      <div className="flex justify-between text-xs text-muted-foreground">
        <span className={side === "long" ? "text-loss" : "text-profit"}>
          {leftLabel} {formatPrice(leftPrice, symbol)}
        </span>
        <span className={side === "long" ? "text-profit" : "text-loss"}>
          {rightLabel} {formatPrice(rightPrice, symbol)}
        </span>
      </div>

      {/* 进度条 */}
      <div className="relative h-2 bg-secondary rounded-full overflow-hidden">
        {/* 入场价格标记线 */}
        <div className="absolute top-0 bottom-0 w-0.5 bg-foreground/60 z-10" style={{ left: `${entryPosition}%` }} />

        {/* 盈亏区域填充 */}
        {currentPosition !== entryPosition && (
          <div
            className={cn(
              "absolute top-0 bottom-0 transition-all duration-300",
              isInProfit ? "bg-profit/60" : "bg-loss/60",
            )}
            style={{
              left: `${Math.min(currentPosition, entryPosition)}%`,
              width: `${Math.abs(currentPosition - entryPosition)}%`,
            }}
          />
        )}

        {/* 当前价格指示器 */}
        <div
          className={cn(
            "absolute top-1/2 -translate-y-1/2 w-3 h-3 rounded-full border-2 border-background transition-all duration-300 z-20",
            isInProfit ? "bg-profit" : "bg-loss",
          )}
          style={{ left: `calc(${currentPosition}% - 6px)` }}
        />
      </div>

      {/* 入场价标签 */}
      <div className="relative h-4">
        <div
          className="absolute text-xs text-muted-foreground -translate-x-1/2 whitespace-nowrap"
          style={{ left: `${entryPosition}%` }}
        >
          入场 {formatPrice(entryPrice, symbol)}
        </div>
      </div>
    </div>
  )
}
