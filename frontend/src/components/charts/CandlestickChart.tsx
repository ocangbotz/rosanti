import {
  CrosshairMode,
  type IChartApi,
  type ISeriesApi,
  type SeriesMarker,
  type Time,
  type UTCTimestamp,
  createChart,
} from "lightweight-charts";
import { useEffect, useRef } from "react";

import { getChartTokens } from "@/lib/chartTokens";
import type { OHLCCandle } from "@/types";

export interface PriceLineSpec {
  price: number;
  color: string;
  title: string;
  lineStyle?: "solid" | "dashed";
}

export interface ChartMarkerSpec {
  time: string;
  position: "aboveBar" | "belowBar";
  color: string;
  shape: "arrowUp" | "arrowDown" | "circle";
  text: string;
}

interface CandlestickChartProps {
  candles: OHLCCandle[];
  priceLines?: PriceLineSpec[];
  markers?: ChartMarkerSpec[];
  height?: number;
}

function toUnixSeconds(iso: string): UTCTimestamp {
  return Math.floor(new Date(iso).getTime() / 1000) as UTCTimestamp;
}

export function CandlestickChart({ candles, priceLines = [], markers = [], height = 420 }: CandlestickChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const tokens = getChartTokens();

    const chart = createChart(containerRef.current, {
      height,
      layout: {
        background: { color: "transparent" },
        textColor: tokens.inkSecondary,
        fontFamily: "system-ui, -apple-system, Segoe UI, sans-serif",
      },
      grid: {
        vertLines: { color: tokens.gridline },
        horzLines: { color: tokens.gridline },
      },
      rightPriceScale: { borderColor: tokens.gridline },
      timeScale: { borderColor: tokens.gridline, timeVisible: true, secondsVisible: false },
      crosshair: { mode: CrosshairMode.Normal },
    });

    const series = chart.addCandlestickSeries({
      upColor: tokens.bull,
      downColor: tokens.bear,
      borderUpColor: tokens.bull,
      borderDownColor: tokens.bear,
      wickUpColor: tokens.bull,
      wickDownColor: tokens.bear,
    });

    chartRef.current = chart;
    seriesRef.current = series;

    // The browser can have already queued a ResizeObserver notification by
    // the time cleanup runs `disconnect()` below — `disconnect()` only
    // stops *future* notifications, not one already in flight. Without this
    // flag, that queued callback fires `chart.applyOptions()` on an
    // already-`remove()`d chart, which throws "Object is disposed" from
    // inside lightweight-charts' internal repaint (verified against a real
    // browser: rapid unmount right after mount reproduces it every time).
    let disposed = false;
    const resizeObserver = new ResizeObserver((entries) => {
      if (disposed) return;
      const entry = entries[0];
      if (entry) chart.applyOptions({ width: entry.contentRect.width });
    });
    resizeObserver.observe(containerRef.current);

    return () => {
      disposed = true;
      resizeObserver.disconnect();
      // lightweight-charts sets up its OWN internal resize/DPI observer on
      // the container (separate from ours above) to track canvas pixel
      // density. That internal observer can already have a notification
      // queued by the browser at the moment we unmount; disposing
      // synchronously here tears the chart down mid-flight and its queued
      // callback then throws "Object is disposed" from inside the
      // library's repaint. Deferring disposal by one animation frame lets
      // any already-queued internal repaint finish against a still-valid
      // chart first (confirmed against a real browser: without this defer,
      // navigating away from the Market page within ~1s of it mounting
      // reproduced the error on every run).
      chartRef.current = null;
      seriesRef.current = null;
      requestAnimationFrame(() => {
        chart.remove();
      });
    };
  }, [height]);

  useEffect(() => {
    const series = seriesRef.current;
    if (!series || candles.length === 0) return;

    series.setData(
      candles.map((c) => ({
        time: toUnixSeconds(c.time) as Time,
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
      })),
    );
    chartRef.current?.timeScale().fitContent();
  }, [candles]);

  useEffect(() => {
    const series = seriesRef.current;
    if (!series) return;

    const created = priceLines.map((line) =>
      series.createPriceLine({
        price: line.price,
        color: line.color,
        lineWidth: 1,
        lineStyle: line.lineStyle === "dashed" ? 2 : 0,
        axisLabelVisible: true,
        title: line.title,
      }),
    );

    return () => {
      // On full unmount, this cleanup can run after the chart-creation
      // effect's cleanup already called `chart.remove()`, leaving `series`
      // disposed — removePriceLine on it throws. There's nothing left to
      // clean up in that case (the whole chart is gone), so it's safe to
      // ignore.
      created.forEach((priceLine) => {
        try {
          series.removePriceLine(priceLine);
        } catch {
          // Series already disposed by the chart-creation effect's cleanup.
        }
      });
    };
  }, [priceLines]);

  useEffect(() => {
    const series = seriesRef.current;
    if (!series) return;

    const seriesMarkers: SeriesMarker<Time>[] = markers
      .map((m) => ({
        time: toUnixSeconds(m.time) as Time,
        position: m.position,
        color: m.color,
        shape: m.shape,
        text: m.text,
      }))
      .sort((a, b) => (a.time as number) - (b.time as number));

    series.setMarkers(seriesMarkers);
  }, [markers]);

  return <div ref={containerRef} className="w-full" />;
}
