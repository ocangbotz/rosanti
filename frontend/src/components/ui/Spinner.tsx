import { Loader2 } from "lucide-react";

import { cn } from "@/lib/cn";

export function Spinner({ className, size = 20 }: { className?: string; size?: number }) {
  return <Loader2 className={cn("animate-spin text-accent", className)} size={size} />;
}

export function LoadingState({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-ink-muted">
      <Spinner size={28} />
      <span className="text-sm">{label}</span>
    </div>
  );
}
