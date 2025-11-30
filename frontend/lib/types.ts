export type TradeStatus = "未进场" | "浮盈" | "浮亏" | "已止盈" | "已止损" | "带单主动止盈" | "带单主动止损" | "部分出局" | "部分止盈" | "部分止损"

export type TradeSide = "long" | "short"

export interface TradeUpdate {
  id: number
  text: string
  status: string
  pnl_points: number
  created_at: number
  created_at_str: string
}

export interface Trade {
  id: number
  channel_id: string
  channel_name: string
  symbol: string
  side: TradeSide
  entry_price: number
  take_profit: number
  stop_loss: number
  current_price: number
  status: TradeStatus
  pnl_points: number
  pnl_percent: number
  created_at: number
  created_at_str: string
  updated_at?: number
  updates?: TradeUpdate[]
  exited_pnl_points?: number  // 已出局部分的盈亏（用于部分出局）
  remaining_pnl_points?: number  // 剩余部分的盈亏（用于部分出局）
}

export interface Trader {
  id: string
  name: string
  avatar?: string
  channel_id: string
  channel_name: string
}

export interface TradesResponse {
  success: boolean
  data: Trade[]
}

export interface PricesResponse {
  success: boolean
  data: Record<string, number>
}

export interface TradersResponse {
  success: boolean
  data: Trader[]
}

export type StatusFilter = "all" | TradeStatus
export type SideFilter = "all" | TradeSide
