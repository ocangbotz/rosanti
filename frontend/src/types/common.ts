// Shared primitive types mirroring backend enums (app/core/constants.py).
// Field names intentionally match the FastAPI/Pydantic JSON keys (snake_case)
// so the API layer needs no case-conversion mapping.

export type Timeframe = "M1" | "M5" | "M15" | "M30" | "H1" | "H4" | "D1" | "W1";

export type TradeDirection = "BUY" | "SELL" | "NEUTRAL";

export type TradingSession = "SYDNEY" | "TOKYO" | "LONDON" | "NEW_YORK" | "OFF_HOURS";

export type VolatilityRegime = "LOW" | "NORMAL" | "HIGH" | "EXTREME";

export type NewsImpact = "LOW" | "MEDIUM" | "HIGH";

export type TradeStatus = "OPEN" | "CLOSED" | "CANCELLED";

export type TradeOutcome = "WIN" | "LOSS" | "BREAKEVEN" | "PENDING";

export type SetupStatus = "PROPOSED" | "TAKEN" | "INVALIDATED" | "EXPIRED";

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export const TIMEFRAMES: Timeframe[] = ["M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1"];
