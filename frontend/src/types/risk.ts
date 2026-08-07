export interface RiskSettings {
  id: number;
  created_at: string;
  updated_at: string;
  account_id: number | null;
  risk_percent: number;
  max_daily_loss_percent: number;
  max_trades_per_day: number;
  max_drawdown_percent: number;
  breakeven_trigger_r: number;
}

export interface RiskSettingsUpdate {
  risk_percent?: number;
  max_daily_loss_percent?: number;
  max_trades_per_day?: number;
  max_drawdown_percent?: number;
  breakeven_trigger_r?: number;
}

export interface LotSizeRequest {
  account_balance: number;
  risk_percent: number;
  entry_price: number;
  stop_loss: number;
  symbol: string;
  pip_value_per_lot?: number;
  pip_size?: number;
}

export interface LotSizeResponse {
  lot_size: number;
  risk_amount: number;
  stop_loss_pips: number;
  pip_value_per_lot: number;
}

export interface BreakevenRequest {
  entry_price: number;
  stop_loss: number;
  current_price: number;
  direction: "BUY" | "SELL";
  trigger_r?: number;
}

export interface BreakevenResponse {
  current_r_multiple: number;
  breakeven_reached: boolean;
  suggested_new_stop_loss: number | null;
}

export interface DailyLimitCheckResponse {
  can_trade: boolean;
  trades_taken_today: number;
  max_trades_per_day: number;
  daily_pnl_percent: number;
  max_daily_loss_percent: number;
  reasons: string[];
}

export interface DrawdownInfo {
  peak_equity: number;
  trough_equity: number;
  current_equity: number;
  current_drawdown_percent: number;
  max_drawdown_observed_percent: number;
  max_drawdown_limit_percent: number;
  limit_breached: boolean;
}
