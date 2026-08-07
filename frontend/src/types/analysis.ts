import type { Timeframe, TradeDirection, TradingSession, VolatilityRegime } from "./common";

export interface IndicatorSnapshot {
  price: number;
  ema20: number;
  ema50: number;
  ema200: number;
  rsi14: number;
  macd_line: number;
  macd_signal: number;
  macd_histogram: number;
  atr14: number;
  volume: number;
  volume_sma20: number;
  relative_volume: number;
  is_volume_spike: boolean;
  ema_trend_bias: TradeDirection;
  rsi_state: string;
}

export interface SwingPoint {
  index: number;
  time: string;
  price: number;
  kind: "HIGH" | "LOW";
}

export interface StructureEvent {
  time: string;
  price: number;
  direction: TradeDirection;
  reference_swing: SwingPoint;
}

export interface StructureAnalysis {
  swing_points: SwingPoint[];
  trend: TradeDirection;
  bos_events: StructureEvent[];
  choch_events: StructureEvent[];
  last_bos: StructureEvent | null;
  last_choch: StructureEvent | null;
}

export interface LiquiditySweep {
  time: string;
  wick_price: number;
  swept_level: number;
  direction: TradeDirection;
}

export interface OrderBlock {
  time: string;
  top: number;
  bottom: number;
  direction: TradeDirection;
  mitigated: boolean;
}

export interface FairValueGap {
  time: string;
  top: number;
  bottom: number;
  direction: TradeDirection;
  filled: boolean;
}

export interface LiquidityAnalysis {
  sweeps: LiquiditySweep[];
  order_blocks: OrderBlock[];
  fair_value_gaps: FairValueGap[];
}

export interface SRLevel {
  price: number;
  kind: "SUPPORT" | "RESISTANCE";
  touches: number;
  last_touch_time: string;
}

export interface SupplyDemandZone {
  top: number;
  bottom: number;
  kind: "SUPPLY" | "DEMAND";
  formed_at: string;
  tested: boolean;
}

export interface LevelsAnalysis {
  support_resistance: SRLevel[];
  supply_demand_zones: SupplyDemandZone[];
}

export interface SessionInfo {
  session: TradingSession;
  is_overlap: boolean;
  as_of: string;
}

export interface VolatilityInfo {
  atr: number;
  atr_percentile: number;
  regime: VolatilityRegime;
}

export interface MarketAnalysis {
  symbol: string;
  timeframe: Timeframe;
  generated_at: string;
  candles_analyzed: number;
  indicators: IndicatorSnapshot;
  structure: StructureAnalysis;
  liquidity: LiquidityAnalysis;
  levels: LevelsAnalysis;
  session: SessionInfo;
  volatility: VolatilityInfo;
}

export interface OHLCCandle {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface OHLCResponse {
  symbol: string;
  timeframe: Timeframe;
  candles: OHLCCandle[];
}

export interface NarrativeResponse {
  symbol: string;
  timeframe: Timeframe;
  narrative: string;
}
