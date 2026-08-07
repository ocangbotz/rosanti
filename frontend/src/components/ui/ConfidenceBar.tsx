import { cn } from "@/lib/cn";
import type { TradeDirection } from "@/types";

interface ConfidenceBarProps {
  confidence: number;
  direction: TradeDirection;
  className?: string;
}

export function ConfidenceBar({ confidence, direction, className }: ConfidenceBarProps) {
  const clamped = Math.max(0, Math.min(100, confidence));
  const barColor = direction === "BUY" ? "bg-bull" : direction === "SELL" ? "bg-bear" : "bg-ink-muted";

  return (
    <div className={cn("flex items-center gap-3", className)}>
      <div className="h-2 flex-1 overflow-hidden rounded-full bg-surface-raised">
        <div
          className={cn("h-full rounded-full transition-all", barColor)}
          style={{ width: `${clamped}%` }}
          role="progressbar"
          aria-valuenow={clamped}
          aria-valuemin={0}
          aria-valuemax={100}
        />
      </div>
      <span className="w-11 shrink-0 text-right text-sm font-semibold tabular-nums text-ink-primary">
        {clamped.toFixed(0)}%
      </span>
    </div>
  );
}
