"use client"

import { Card, CardContent } from "@/components/ui/card"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { cn } from "@/lib/utils"
import type { Trader } from "@/lib/types"
import { Users, ChevronRight } from "lucide-react"

interface TraderSelectorProps {
  traders: Trader[]
  selectedTrader: Trader | null
  onSelect: (trader: Trader) => void
  isLoading?: boolean
}

export function TraderSelector({ traders, selectedTrader, onSelect, isLoading }: TraderSelectorProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {[1, 2, 3].map((i) => (
          <Card key={i} className="animate-pulse bg-card">
            <CardContent className="p-4 flex items-center gap-4">
              <div className="w-12 h-12 rounded-full bg-muted" />
              <div className="flex-1 space-y-2">
                <div className="h-4 bg-muted rounded w-20" />
                <div className="h-3 bg-muted rounded w-32" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 text-muted-foreground">
        <Users className="w-5 h-5" />
        <span className="text-sm">选择带单员查看交易详情</span>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {traders.map((trader) => (
          <Card
            key={trader.id}
            className={cn(
              "cursor-pointer transition-all duration-200 hover:shadow-lg hover:shadow-black/20",
              selectedTrader?.id === trader.id ? "border-primary bg-primary/10" : "bg-card hover:bg-accent/50",
            )}
            onClick={() => onSelect(trader)}
          >
            <CardContent className="p-4 flex items-center gap-4">
              <Avatar className="w-12 h-12">
                <AvatarImage src={trader.avatar || "/placeholder.svg"} alt={trader.name} />
                <AvatarFallback className="bg-primary/20 text-primary">{trader.name.slice(0, 2)}</AvatarFallback>
              </Avatar>
              <div className="flex-1 min-w-0">
                <h3 className="font-semibold truncate">{trader.name}</h3>
                <p className="text-sm text-muted-foreground truncate">{trader.channel_name}</p>
              </div>
              <ChevronRight
                className={cn(
                  "w-5 h-5 transition-colors",
                  selectedTrader?.id === trader.id ? "text-primary" : "text-muted-foreground",
                )}
              />
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
