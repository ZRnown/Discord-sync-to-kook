import type { TradeStatus } from "@/lib/types"
import { getStatusColor } from "@/lib/trade-utils"
import { cn } from "@/lib/utils"

interface StatusBadgeProps {
  status: TradeStatus
  className?: string
  size?: "default" | "sm"
}

export function StatusBadge({ status, className, size = "default" }: StatusBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full font-medium",
        size === "sm" ? "px-1.5 py-0.5 text-[10px]" : "px-2.5 py-0.5 text-xs",
        getStatusColor(status),
        className,
      )}
    >
      {status}
    </span>
  )
}
