import type { Trade, TradeStatus, TradeUpdate } from "./types"

export function getStatusColor(status: TradeStatus): string {
  const colorMap: Record<TradeStatus, string> = {
    待入场: "bg-muted text-muted-foreground",
    未进场: "bg-neutral text-foreground",
    浮盈: "bg-profit text-primary-foreground",
    浮亏: "bg-loss text-destructive-foreground",
    已止盈: "bg-profit-muted text-profit",
    已止损: "bg-loss-muted text-loss",
    带单主动止盈: "bg-info text-foreground",
    带单主动止损: "bg-warning text-primary-foreground",
    部分出局: "bg-info/80 text-foreground",
    部分止盈: "bg-profit/60 text-primary-foreground",
    部分止损: "bg-loss/60 text-destructive-foreground",
  }
  return colorMap[status] || "bg-neutral text-foreground"
}

export function getStatusBorderColor(status: TradeStatus): string {
  const colorMap: Record<TradeStatus, string> = {
    待入场: "border-muted/50",
    未进场: "border-neutral/50",
    浮盈: "border-profit/50",
    浮亏: "border-loss/50",
    已止盈: "border-profit/30",
    已止损: "border-loss/30",
    带单主动止盈: "border-info/50",
    带单主动止损: "border-warning/50",
    部分出局: "border-info/40",
    部分止盈: "border-profit/40",
    部分止损: "border-loss/40",
  }
  return colorMap[status] || "border-neutral/50"
}

export function calculatePricePosition(
  current: number,
  stopLoss: number,
  entry: number,
  takeProfit: number,
  side: "long" | "short",
): number {
  if (side === "long") {
    const range = takeProfit - stopLoss
    if (range === 0) return 50
    const position = ((current - stopLoss) / range) * 100
    return Math.max(0, Math.min(100, position))
  } else {
    // 空单：止盈在下方，止损在上方
    const range = stopLoss - takeProfit
    if (range === 0) return 50
    const position = ((stopLoss - current) / range) * 100
    return Math.max(0, Math.min(100, position))
  }
}

export function calculateEntryPosition(
  stopLoss: number,
  entry: number,
  takeProfit: number,
  side: "long" | "short",
): number {
  if (side === "long") {
    const range = takeProfit - stopLoss
    if (range === 0) return 50
    return ((entry - stopLoss) / range) * 100
  } else {
    const range = stopLoss - takeProfit
    if (range === 0) return 50
    return ((stopLoss - entry) / range) * 100
  }
}

export function formatPrice(price: number | null | undefined, symbol: string): string {
  // 处理 null 或 undefined
  if (price === null || price === undefined || isNaN(price)) {
    return "—"
  }
  
  // 根据币种调整小数位数
  if (symbol.includes("BTC")) {
    return price.toLocaleString("en-US", { minimumFractionDigits: 1, maximumFractionDigits: 1 })
  }
  if (symbol.includes("ETH")) {
    return price.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  }
  // 默认2位小数
  return price.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 4 })
}

export function formatPnL(points: number): string {
  const sign = points >= 0 ? "+" : ""
  return `${sign}${points.toFixed(2)}`
}

export function formatPercent(percent: number): string {
  const sign = percent >= 0 ? "+" : ""
  return `${sign}${percent.toFixed(2)}%`
}

export function calculateTradeStatus(trade: Trade, updates?: TradeUpdate[]): TradeStatus {
  // 1. 优先检查 trade_updates 表中的状态
  const latestUpdate = updates?.[0]
  if (latestUpdate?.status) {
    const endStatuses: TradeStatus[] = ["已止盈", "已止损", "带单主动止盈", "带单主动止损"]
    if (endStatuses.includes(latestUpdate.status as TradeStatus)) {
      return latestUpdate.status as TradeStatus
    }
  }

  // 2. 检查当前价格与进场价的关系
  const { current_price, entry_price, side, take_profit, stop_loss } = trade

  if (!current_price || current_price === 0) {
    return "未进场"
  }

  // 3. 判断是否触发止盈/止损
  if (side === "long") {
    if (current_price >= take_profit) return "已止盈"
    if (current_price <= stop_loss) return "已止损"
  } else {
    if (current_price <= take_profit) return "已止盈"
    if (current_price >= stop_loss) return "已止损"
  }

  // 4. 计算盈亏
  const pnl = side === "long" ? current_price - entry_price : entry_price - current_price

  if (pnl > 0) return "浮盈"
  if (pnl < 0) return "浮亏"
  return "未进场"
}
