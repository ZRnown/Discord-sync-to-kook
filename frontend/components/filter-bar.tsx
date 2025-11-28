"use client"

import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import type { StatusFilter, SideFilter } from "@/lib/types"
import { RefreshCw } from "lucide-react"

interface FilterBarProps {
  statusFilter: StatusFilter
  sideFilter: SideFilter
  symbolFilter: string
  symbols: string[]
  onStatusChange: (status: StatusFilter) => void
  onSideChange: (side: SideFilter) => void
  onSymbolChange: (symbol: string) => void
  onRefresh: () => void
  isLoading?: boolean
}

const statusOptions: { value: StatusFilter; label: string }[] = [
  { value: "all", label: "全部状态" },
  { value: "未进场", label: "未进场" },
  { value: "浮盈", label: "浮盈" },
  { value: "浮亏", label: "浮亏" },
  { value: "已止盈", label: "已止盈" },
  { value: "已止损", label: "已止损" },
  { value: "带单主动止盈", label: "带单主动止盈" },
  { value: "带单主动止损", label: "带单主动止损" },
]

const sideOptions: { value: SideFilter; label: string }[] = [
  { value: "all", label: "全部方向" },
  { value: "long", label: "多单" },
  { value: "short", label: "空单" },
]

export function FilterBar({
  statusFilter,
  sideFilter,
  symbolFilter,
  symbols,
  onStatusChange,
  onSideChange,
  onSymbolChange,
  onRefresh,
  isLoading,
}: FilterBarProps) {
  return (
    <div className="flex flex-wrap items-center gap-3 p-4 bg-card rounded-lg border border-border">
      <Select value={statusFilter} onValueChange={(v) => onStatusChange(v as StatusFilter)}>
        <SelectTrigger className="w-[140px]">
          <SelectValue placeholder="状态筛选" />
        </SelectTrigger>
        <SelectContent>
          {statusOptions.map((opt) => (
            <SelectItem key={opt.value} value={opt.value}>
              {opt.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select value={sideFilter} onValueChange={(v) => onSideChange(v as SideFilter)}>
        <SelectTrigger className="w-[120px]">
          <SelectValue placeholder="方向筛选" />
        </SelectTrigger>
        <SelectContent>
          {sideOptions.map((opt) => (
            <SelectItem key={opt.value} value={opt.value}>
              {opt.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select value={symbolFilter} onValueChange={onSymbolChange}>
        <SelectTrigger className="w-[160px]">
          <SelectValue placeholder="交易对筛选" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">全部交易对</SelectItem>
          {symbols.map((symbol) => (
            <SelectItem key={symbol} value={symbol}>
              {symbol}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Button variant="outline" size="icon" onClick={onRefresh} disabled={isLoading} className="ml-auto bg-transparent">
        <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`} />
      </Button>
    </div>
  )
}
