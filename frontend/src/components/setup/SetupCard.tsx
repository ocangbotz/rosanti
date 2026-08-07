import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { ConfidenceBar } from "@/components/ui/ConfidenceBar";
import { DirectionBadge } from "@/components/ui/Badge";
import { formatDateTime, formatPrice } from "@/lib/format";
import type { TradeSetup } from "@/types";

export function SetupCard({ setup }: { setup: TradeSetup }) {
  const digits = setup.symbol.toUpperCase().includes("JPY") ? 3 : 5;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <CardTitle>{setup.symbol}</CardTitle>
          <span className="text-xs text-ink-muted">{setup.timeframe}</span>
        </div>
        <div className="flex items-center gap-2">
          <DirectionBadge direction={setup.direction} />
          <span className="text-xs text-ink-muted">{formatDateTime(setup.created_at)}</span>
        </div>
      </CardHeader>
      <CardBody className="space-y-4">
        <ConfidenceBar confidence={setup.confidence_score} direction={setup.direction} />

        <div className="grid grid-cols-4 gap-3 text-sm">
          <PriceStat label="Entry" value={setup.entry_price} digits={digits} />
          <PriceStat label="Stop Loss" value={setup.stop_loss} digits={digits} tone="bad" />
          <PriceStat label="Take Profit" value={setup.take_profit} digits={digits} tone="good" />
          <div>
            <p className="text-xs text-ink-muted">Risk/Reward</p>
            <p className="font-semibold tabular-nums text-ink-primary">1:{setup.risk_reward.toFixed(2)}</p>
          </div>
        </div>

        {setup.ai_narrative && (
          <div className="rounded-lg border border-border bg-surface-raised p-3 text-sm text-ink-secondary">
            {setup.ai_narrative}
          </div>
        )}

        {setup.reasons.length > 0 && (
          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-muted">
              Why this setup
            </p>
            <ul className="space-y-1.5">
              {setup.reasons.map((reason) => (
                <li key={reason.factor} className="flex items-start gap-2 text-sm text-ink-secondary">
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />
                  <span>{reason.description}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardBody>
    </Card>
  );
}

function PriceStat({
  label,
  value,
  digits,
  tone,
}: {
  label: string;
  value: number;
  digits: number;
  tone?: "good" | "bad";
}) {
  return (
    <div>
      <p className="text-xs text-ink-muted">{label}</p>
      <p
        className={
          "font-semibold tabular-nums " +
          (tone === "good" ? "text-delta-good" : tone === "bad" ? "text-delta-bad" : "text-ink-primary")
        }
      >
        {formatPrice(value, digits)}
      </p>
    </div>
  );
}
