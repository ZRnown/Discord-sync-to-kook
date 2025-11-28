"use client"

import { useEffect, useRef, useState } from "react"
import { cn } from "@/lib/utils"
import { usePrices } from "@/hooks/use-trades"
import { TrendingUp, TrendingDown } from "lucide-react"

export function PriceTicker() {
  const { prices, isLoading } = usePrices()
  const prevPricesRef = useRef<Record<string, number>>({})
  const [animations, setAnimations] = useState<Record<string, "up" | "down" | null>>({})

  useEffect(() => {
    const newAnimations: Record<string, "up" | "down" | null> = {}
    Object.entries(prices).forEach(([symbol, price]) => {
      const prevPrice = prevPricesRef.current[symbol]
      if (prevPrice && price !== prevPrice) {
        newAnimations[symbol] = price > prevPrice ? "up" : "down"
      }
    })

    if (Object.keys(newAnimations).length > 0) {
      setAnimations(newAnimations)
      const timer = setTimeout(() => setAnimations({}), 500)
      return () => clearTimeout(timer)
    }

    prevPricesRef.current = prices
  }, [prices])

  const formatPrice = (price: number, symbol: string) => {
    if (symbol.includes("BTC")) {
      return price.toLocaleString("en-US", { minimumFractionDigits: 1, maximumFractionDigits: 1 })
    }
    return price.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  }

  const coins = [
    { symbol: "BTC-USDT-SWAP", name: "BTC" },
    { symbol: "ETH-USDT-SWAP", name: "ETH" },
  ]

  if (isLoading) {
    return (
      <div className="flex items-center gap-4 text-xs">
        {coins.map((coin) => (
          <div key={coin.symbol} className="flex items-center gap-1 animate-pulse">
            <span className="text-muted-foreground">{coin.name}</span>
            <span className="bg-muted rounded w-16 h-4" />
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className="flex items-center gap-4 text-xs">
      {coins.map((coin) => {
        const price = prices[coin.symbol]
        const animation = animations[coin.symbol]

        return (
          <div key={coin.symbol} className="flex items-center gap-1.5">
            <span className="text-muted-foreground">{coin.name}</span>
            <span
              className={cn(
                "font-mono font-medium transition-colors",
                animation === "up" && "text-profit price-up",
                animation === "down" && "text-loss price-down",
                !animation && "text-foreground",
              )}
            >
              ${price ? formatPrice(price, coin.symbol) : "--"}
            </span>
            {animation === "up" && <TrendingUp className="w-3 h-3 text-profit" />}
            {animation === "down" && <TrendingDown className="w-3 h-3 text-loss" />}
          </div>
        )
      })}
    </div>
  )
}
