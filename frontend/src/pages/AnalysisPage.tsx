import { Sparkles, Upload } from "lucide-react";
import { useState } from "react";

import { getMarketAnalysis, getMarketNarrative } from "@/api/analysis";
import { analyzeScreenshot } from "@/api/screenshot";
import { generateSetup } from "@/api/setups";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState, Spinner } from "@/components/ui/Spinner";
import { SetupCard } from "@/components/setup/SetupCard";
import { extractErrorMessage } from "@/lib/apiClient";
import { formatPrice } from "@/lib/format";
import { useApi } from "@/lib/useApi";
import { useAppStore } from "@/store/useAppStore";
import type { ScreenshotAnalysis, TradeSetup } from "@/types";

export function AnalysisPage() {
  const { selectedSymbol, selectedTimeframe } = useAppStore();
  const analysis = useApi(() => getMarketAnalysis(selectedSymbol, selectedTimeframe, 300), [
    selectedSymbol,
    selectedTimeframe,
  ]);

  const [setup, setSetup] = useState<TradeSetup | null>(null);
  const [setupLoading, setSetupLoading] = useState(false);
  const [setupError, setSetupError] = useState<string | null>(null);

  const [narrative, setNarrative] = useState<string | null>(null);
  const [narrativeLoading, setNarrativeLoading] = useState(false);
  const [narrativeError, setNarrativeError] = useState<string | null>(null);

  async function handleGenerateSetup() {
    setSetupLoading(true);
    setSetupError(null);
    try {
      const result = await generateSetup({
        symbol: selectedSymbol,
        timeframe: selectedTimeframe,
        include_ai_narrative: false,
      });
      setSetup(result);
    } catch (err) {
      setSetupError(extractErrorMessage(err));
    } finally {
      setSetupLoading(false);
    }
  }

  async function handleGetNarrative() {
    setNarrativeLoading(true);
    setNarrativeError(null);
    try {
      const result = await getMarketNarrative(selectedSymbol, selectedTimeframe, 300);
      setNarrative(result.narrative);
    } catch (err) {
      setNarrativeError(extractErrorMessage(err));
    } finally {
      setNarrativeLoading(false);
    }
  }

  const ind = analysis.data?.indicators;
  const structure = analysis.data?.structure;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-ink-primary">
            Analysis — {selectedSymbol} <span className="text-ink-muted">· {selectedTimeframe}</span>
          </h1>
          <p className="text-sm text-ink-muted">
            Structure, confluence, and risk — no blind signals, only reasons.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={handleGetNarrative} disabled={narrativeLoading}>
            {narrativeLoading ? <Spinner size={16} /> : <Sparkles size={16} />}
            AI Narrative
          </Button>
          <Button onClick={handleGenerateSetup} disabled={setupLoading}>
            {setupLoading && <Spinner size={16} />}
            Generate Trade Setup
          </Button>
        </div>
      </div>

      {analysis.loading && !analysis.data ? (
        <LoadingState label="Running analysis…" />
      ) : analysis.error ? (
        <ErrorState message={analysis.error} onRetry={analysis.refetch} />
      ) : analysis.data && ind && structure ? (
        <>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
            <MetricTile label="Price" value={formatPrice(ind.price)} />
            <MetricTile label="EMA Trend" value={<Badge tone={toneFor(ind.ema_trend_bias)}>{ind.ema_trend_bias}</Badge>} />
            <MetricTile label="RSI (14)" value={ind.rsi14.toFixed(1)} sub={ind.rsi_state.replace(/_/g, " ")} />
            <MetricTile label="MACD Hist" value={ind.macd_histogram.toFixed(5)} />
            <MetricTile label="ATR (14)" value={ind.atr14.toFixed(5)} />
            <MetricTile
              label="Rel. Volume"
              value={`${ind.relative_volume.toFixed(1)}x`}
              sub={ind.is_volume_spike ? "spike" : undefined}
            />
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            <Card>
              <CardHeader>
                <CardTitle>Market Structure</CardTitle>
              </CardHeader>
              <CardBody className="space-y-3 text-sm">
                <Row label="Trend" value={<Badge tone={toneFor(structure.trend)}>{structure.trend}</Badge>} />
                <Row
                  label="Last BOS"
                  value={
                    structure.last_bos
                      ? `${structure.last_bos.direction} @ ${formatPrice(structure.last_bos.price)}`
                      : "None"
                  }
                />
                <Row
                  label="Last CHOCH"
                  value={
                    structure.last_choch
                      ? `${structure.last_choch.direction} @ ${formatPrice(structure.last_choch.price)}`
                      : "None"
                  }
                />
                <Row label="Session" value={analysis.data.session.session} />
                <Row label="Volatility" value={analysis.data.volatility.regime} />
              </CardBody>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Liquidity</CardTitle>
              </CardHeader>
              <CardBody className="space-y-3 text-sm">
                <Row label="Liquidity sweeps" value={analysis.data.liquidity.sweeps.length} />
                <Row
                  label="Unmitigated order blocks"
                  value={analysis.data.liquidity.order_blocks.filter((o) => !o.mitigated).length}
                />
                <Row
                  label="Unfilled fair value gaps"
                  value={analysis.data.liquidity.fair_value_gaps.filter((f) => !f.filled).length}
                />
              </CardBody>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Key Levels</CardTitle>
              </CardHeader>
              <CardBody>
                <ul className="max-h-40 space-y-1.5 overflow-y-auto text-sm">
                  {analysis.data.levels.support_resistance.slice(0, 8).map((level) => (
                    <li key={`${level.kind}-${level.price}`} className="flex items-center justify-between">
                      <span className={level.kind === "SUPPORT" ? "text-bull" : "text-bear"}>
                        {level.kind}
                      </span>
                      <span className="tabular-nums text-ink-secondary">
                        {formatPrice(level.price)} ({level.touches}x)
                      </span>
                    </li>
                  ))}
                </ul>
              </CardBody>
            </Card>
          </div>
        </>
      ) : null}

      {narrativeError && <ErrorState message={narrativeError} />}
      {narrative && (
        <Card>
          <CardHeader>
            <CardTitle>AI Narrative</CardTitle>
          </CardHeader>
          <CardBody>
            <p className="text-sm leading-relaxed text-ink-secondary">{narrative}</p>
          </CardBody>
        </Card>
      )}

      {setupError && <ErrorState message={setupError} />}
      {setup && <SetupCard setup={setup} />}

      <ScreenshotAnalyzerCard defaultSymbolHint={selectedSymbol} />
    </div>
  );
}

function toneFor(direction: string): "bull" | "bear" | "neutral" {
  if (direction === "BUY") return "bull";
  if (direction === "SELL") return "bear";
  return "neutral";
}

function MetricTile({ label, value, sub }: { label: string; value: React.ReactNode; sub?: string }) {
  return (
    <div className="rounded-xl border border-border bg-surface-card p-3">
      <p className="text-[11px] uppercase tracking-wide text-ink-muted">{label}</p>
      <p className="mt-1 text-base font-semibold tabular-nums text-ink-primary">{value}</p>
      {sub && <p className="text-xs capitalize text-ink-muted">{sub}</p>}
    </div>
  );
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-ink-muted">{label}</span>
      <span className="font-medium text-ink-primary">{value}</span>
    </div>
  );
}

function ScreenshotAnalyzerCard({ defaultSymbolHint }: { defaultSymbolHint: string }) {
  const [file, setFile] = useState<File | null>(null);
  const [symbolHint, setSymbolHint] = useState(defaultSymbolHint);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ScreenshotAnalysis | null>(null);

  async function handleUpload() {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const analyzed = await analyzeScreenshot(file, symbolHint || undefined);
      setResult(analyzed);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Screenshot Analysis</CardTitle>
      </CardHeader>
      <CardBody className="space-y-4">
        <p className="text-sm text-ink-muted">
          Upload a chart screenshot for an AI review of trend, key levels, a possible entry/SL/TP, and
          any visible mistakes in the setup.
        </p>
        <div className="flex flex-wrap items-center gap-3">
          <label className="flex cursor-pointer items-center gap-2 rounded-lg border border-dashed border-border px-4 py-2 text-sm text-ink-secondary hover:border-accent hover:text-ink-primary">
            <Upload size={16} />
            {file ? file.name : "Choose image"}
            <input
              type="file"
              accept="image/png,image/jpeg,image/webp"
              className="hidden"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
          </label>
          <input
            value={symbolHint}
            onChange={(e) => setSymbolHint(e.target.value)}
            placeholder="Symbol hint (optional)"
            className="w-44 rounded-lg border border-border bg-surface-raised px-3 py-2 text-sm text-ink-primary outline-none focus:border-accent"
          />
          <Button onClick={handleUpload} disabled={!file || loading}>
            {loading && <Spinner size={16} />}
            Analyze
          </Button>
        </div>

        {error && <ErrorState message={error} />}

        {result && (
          <div className="space-y-3 rounded-lg border border-border bg-surface-raised p-4">
            <div className="flex flex-wrap items-center gap-2">
              {result.detected_trend && <Badge tone={toneFor(result.detected_trend.toUpperCase())}>{result.detected_trend}</Badge>}
              {result.suggested_entry && (
                <span className="text-sm text-ink-secondary">Entry ~{formatPrice(result.suggested_entry)}</span>
              )}
              {result.suggested_stop_loss && (
                <span className="text-sm text-ink-secondary">
                  SL ~{formatPrice(result.suggested_stop_loss)}
                </span>
              )}
              {result.suggested_take_profit && (
                <span className="text-sm text-ink-secondary">
                  TP ~{formatPrice(result.suggested_take_profit)}
                </span>
              )}
            </div>
            <p className="text-sm leading-relaxed text-ink-secondary">{result.full_report}</p>
            {result.mistakes.length > 0 && (
              <div>
                <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-status-warning">
                  Potential mistakes
                </p>
                <ul className="list-inside list-disc space-y-1 text-sm text-ink-secondary">
                  {result.mistakes.map((mistake) => (
                    <li key={mistake}>{mistake}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </CardBody>
    </Card>
  );
}
