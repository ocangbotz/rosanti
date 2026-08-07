import type { SetupStatus, Timeframe, TradeDirection } from "./common";

export interface Reason {
  factor: string;
  description: string;
  direction: TradeDirection;
  weight: number;
}

export interface TradeSetup {
  id: number;
  created_at: string;
  updated_at: string;
  symbol: string;
  timeframe: Timeframe;
  direction: TradeDirection;
  entry_price: number;
  stop_loss: number;
  take_profit: number;
  risk_reward: number;
  confidence_score: number;
  reasons: Reason[];
  structure_snapshot: Record<string, unknown>;
  ai_narrative: string | null;
  status: SetupStatus;
  expires_at: string | null;
}

export interface TradeSetupSummary {
  id: number;
  symbol: string;
  timeframe: Timeframe;
  direction: TradeDirection;
  confidence_score: number;
  risk_reward: number;
  status: SetupStatus;
  created_at: string;
}

export interface GenerateSetupRequest {
  symbol: string;
  timeframe: Timeframe;
  risk_percent?: number | null;
  include_ai_narrative: boolean;
}
