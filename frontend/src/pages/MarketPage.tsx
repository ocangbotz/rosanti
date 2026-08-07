import { useMemo } from "react";

import { getOhlc, getSymbolInfo } from "@/api/market";
import type { ChartMarkerSpec, PriceLineSpec } from "@/components/charts/CandlestickChart";
import { CandlestickChart } from "@/components/charts/CandlestickChart";
import { DirectionBadge } from "@/components/ui/Badge";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/Spinner";
import { getChartTokens } from "@/lib/chartTokens";
import { formatPrice } from "@/lib/format";
import { useApi } from "@/lib/useApi";
import { useMarketStream } from "@/lib/useMarketStream";
import { useAppStore } from "@/store/useAppStore";

export function MarketPage() {
  const { selectedSymbol, selectedTimeframe } = useAppStore();
  const ohlc = useApi(() => getOhlc(selectedSymbol, selectedTimeframe, 300), [
    selectedSymbol,
    selectedTimeframe,
  ]);
  const symbolInfo = useApi(() => getSymbolInfo(selectedSymbol), [selectedSymbol]);
  const { latest, connected } = useMarketStream(selectedSymbol, selectedTimeframe);

  const priceLines = useMemo<PriceLineSpec[]>(() => {
    if (!latest || latest.type !== "market_update" || latest.price === undefined) return [];
    return [{ price: latest.price, color: getChartTokens().accent, title: "Live" }];
  }, [latest]);

  const markers = useMemo<ChartMarkerSpec[]>(() => {
    const list: ChartMarkerSpec[] = [];
    if (latest?.last_bos) {
      const tokens = getChartTokens();
      list.push({
        time: latest.generated_at ?? new Date().toISOString(),
        position: latest.last_bos.direction === "BUY" ? "belowBar" : "aboveBar",
        color: latest.last_bos.direction === "BUY" ? tokens.bull : tokens.bear,
        shape: latest.last_bos.direction === "BUY" ? "arrowUp" : "arrowDown",
        text: "BOS",
      });
    }
    return list;
  }, [latest]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-ink-primary">
            {selectedSymbol} <span className="text-ink-muted">· {selectedTimeframe}</span>
          </h1>
          <p className="flex items-center gap-1.5 text-sm text-ink-muted">
            <span
              className={`h-1.5 w-1.5 rounded-full ${connected ? "bg-status-good" : "bg-status-critical"}`}
            />
            {connected ? "Live" : "Reconnecting…"}
          </p>
        </div>
        {latest?.structure_trend && <DirectionBadge direction={latest.structure_trend} />}
      </div>

      <Card>
        <CardBody className="p-2 sm:p-4">
          {ohlc.loading && !ohlc.data ? (
            <LoadingState label="Loading chart…" />
          ) : ohlc.error ? (
            <ErrorState message={ohlc.error} onRetry={ohlc.refetch} />
          ) : ohlc.data ? (
            <CandlestickChart candles={ohlc.data.candles} priceLines={priceLines} markers={markers} height={480} />
          ) : null}
        </CardBody>
      </Card>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader>
            <CardTitle>Bid / Ask</CardTitle>
          </CardHeader>
          <CardBody>
            {symbolInfo.loading ? (
              <LoadingState />
            ) : symbolInfo.error ? (
              <ErrorState message={symbolInfo.error} />
            ) : symbolInfo.data ? (
              <div className="space-y-1">
                <p className="text-lg font-semibold tabular-nums text-ink-primary">
                  {formatPrice(symbolInfo.data.bid, symbolInfo.data.digits)} /{" "}
                  {formatPrice(symbolInfo.data.ask, symbolInfo.data.digits)}
                </p>
                <p className="text-xs text-ink-muted">Spread: {symbolInfo.data.spread_points} points</p>
              </div>
            ) : null}
          </CardBody>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Session</CardTitle>
          </CardHeader>
          <CardBody>
            <p className="text-lg font-semibold text-ink-primary">{latest?.session ?? "—"}</p>
          </CardBody>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Volatility</CardTitle>
          </CardHeader>
          <CardBody>
            <p className="text-lg font-semibold text-ink-primary">{latest?.volatility_regime ?? "—"}</p>
          </CardBody>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>RSI (14)</CardTitle>
          </CardHeader>
          <CardBody>
            <p className="text-lg font-semibold tabular-nums text-ink-primary">
              {latest?.rsi14 !== undefined ? latest.rsi14.toFixed(1) : "—"}
            </p>
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
