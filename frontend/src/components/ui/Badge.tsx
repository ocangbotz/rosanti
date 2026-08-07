import type { HTMLAttributes, ReactNode } from "react";

import { cn } from "@/lib/cn";

type BadgeTone = "neutral" | "bull" | "bear" | "good" | "warning" | "serious" | "critical" | "accent";

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: BadgeTone;
  children: ReactNode;
}

const toneClasses: Record<BadgeTone, string> = {
  neutral: "bg-surface-raised text-ink-secondary",
  bull: "bg-bull/15 text-bull",
  bear: "bg-bear/15 text-bear",
  good: "bg-status-good/15 text-status-good",
  warning: "bg-status-warning/15 text-status-warning",
  serious: "bg-status-serious/15 text-status-serious",
  critical: "bg-status-critical/15 text-status-critical",
  accent: "bg-accent/15 text-accent",
};

export function Badge({ tone = "neutral", className, children, ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium",
        toneClasses[tone],
        className,
      )}
      {...props}
    >
      {children}
    </span>
  );
}

export function DirectionBadge({ direction }: { direction: "BUY" | "SELL" | "NEUTRAL" }) {
  if (direction === "BUY") return <Badge tone="bull">BUY</Badge>;
  if (direction === "SELL") return <Badge tone="bear">SELL</Badge>;
  return <Badge tone="neutral">NEUTRAL</Badge>;
}
