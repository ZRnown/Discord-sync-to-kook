"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { HistoryTradeCard } from "./history-trade-card"
import type { Trade } from "@/lib/types"
import { ChevronDown, ChevronUp, History } from "lucide-react"

interface HistorySectionProps {
  trades: Trade[]
}

export function HistorySection({ trades }: HistorySectionProps) {
  const [expanded, setExpanded] = useState(false)

  if (trades.length === 0) {
    return null
  }

  return (
    <div className="border-t border-border pt-6 mt-6">
      <Button
        variant="ghost"
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between py-3 h-auto"
      >
        <div className="flex items-center gap-2">
          <History className="w-4 h-4 text-muted-foreground" />
          <span className="font-medium">历史带单</span>
          <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded-full">{trades.length} 单</span>
        </div>
        {expanded ? (
          <ChevronUp className="w-4 h-4 text-muted-foreground" />
        ) : (
          <ChevronDown className="w-4 h-4 text-muted-foreground" />
        )}
      </Button>

      {expanded && (
        <div className="mt-4 space-y-2">
          {trades.map((trade) => (
            <HistoryTradeCard key={trade.id} trade={trade} />
          ))}
        </div>
      )}
    </div>
  )
}
