export type TradeStatus = "未进场" | "浮盈" | "浮亏" | "已止盈" | "已止损" | "带单主动止盈" | "带单主动止损"

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
