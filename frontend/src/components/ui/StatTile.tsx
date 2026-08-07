import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

interface StatTileProps {
  label: string;
  value: ReactNode;
  delta?: ReactNode;
  deltaTone?: "good" | "bad" | "neutral";
  icon?: ReactNode;
  className?: string;
}

export function StatTile({ label, value, delta, deltaTone = "neutral", icon, className }: StatTileProps) {
  return (
    <div className={cn("rounded-xl border border-border bg-surface-card p-4", className)}>
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium uppercase tracking-wide text-ink-muted">{label}</span>
        {icon && <span className="text-ink-muted">{icon}</span>}
      </div>
      <div className="mt-2 text-2xl font-semibold tabular-nums text-ink-primary">{value}</div>
      {delta !== undefined && (
        <div
          className={cn(
            "mt-1 text-xs font-medium tabular-nums",
            deltaTone === "good" && "text-delta-good",
            deltaTone === "bad" && "text-delta-bad",
            deltaTone === "neutral" && "text-ink-secondary",
          )}
        >
          {delta}
        </div>
      )}
    </div>
  );
}
