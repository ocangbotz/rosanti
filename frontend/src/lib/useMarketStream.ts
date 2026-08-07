import { useEffect, useRef, useState } from "react";

import type { Timeframe, TradeDirection, TradingSession, VolatilityRegime } from "@/types";

export interface MarketStreamMessage {
  type: "market_update" | "error";
  symbol?: string;
  timeframe?: Timeframe;
  generated_at?: string;
  price?: number;
  ema_trend_bias?: TradeDirection;
  rsi14?: number;
  structure_trend?: TradeDirection;
  last_bos?: { direction: TradeDirection; price: number } | null;
  last_choch?: { direction: TradeDirection; price: number } | null;
  session?: TradingSession;
  volatility_regime?: VolatilityRegime;
  message?: string;
}

function resolveWsUrl(symbol: string, timeframe: Timeframe): string {
  const explicitBase = import.meta.env.VITE_WS_BASE_URL;
  if (explicitBase) {
    return `${explicitBase}/ws/market?symbol=${symbol}&timeframe=${timeframe}`;
  }
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}/ws/market?symbol=${symbol}&timeframe=${timeframe}`;
}

const RECONNECT_DELAY_MS = 3000;

/**
 * Subscribes to the live `/ws/market` stream for a symbol/timeframe.
 * Reconnects automatically (fixed backoff) if the connection drops —
 * network blips shouldn't require a page refresh on a live dashboard.
 */
export function useMarketStream(symbol: string, timeframe: Timeframe) {
  const [latest, setLatest] = useState<MarketStreamMessage | null>(null);
  const [connected, setConnected] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let cancelled = false;
    let reconnectTimer: ReturnType<typeof setTimeout> | undefined;

    function connect() {
      if (cancelled) return;
      const socket = new WebSocket(resolveWsUrl(symbol, timeframe));
      socketRef.current = socket;

      socket.onopen = () => setConnected(true);

      socket.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data) as MarketStreamMessage;
          setLatest(payload);
        } catch {
          // Ignore malformed frames rather than crashing the stream.
        }
      };

      socket.onclose = () => {
        setConnected(false);
        if (!cancelled) {
          reconnectTimer = setTimeout(connect, RECONNECT_DELAY_MS);
        }
      };

      socket.onerror = () => {
        socket.close();
      };
    }

    connect();

    return () => {
      cancelled = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      socketRef.current?.close();
    };
  }, [symbol, timeframe]);

  return { latest, connected };
}
