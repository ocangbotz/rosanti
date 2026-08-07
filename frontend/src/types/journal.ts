import type { TradeDirection, TradeOutcome } from "./common";

export interface JournalEntry {
  id: number;
  created_at: string;
  updated_at: string;
  setup_id: number | null;
  account_id: number | null;
  mt5_ticket: number | null;
  symbol: string;
  direction: TradeDirection;
  entry_price: number;
  exit_price: number | null;
  stop_loss: number;
  take_profit: number;
  lot_size: number;
  risk_percent: number | null;
  r_multiple: number | null;
  profit_loss: number | null;
  profit_loss_percent: number | null;
  outcome: TradeOutcome;
  opened_at: string;
  closed_at: string | null;
  ai_summary: string | null;
  trader_notes: string | null;
}

export interface JournalEntryCreate {
  setup_id?: number | null;
  account_id?: number | null;
  mt5_ticket?: number | null;
  symbol: string;
  direction: TradeDirection;
  entry_price: number;
  stop_loss: number;
  take_profit: number;
  lot_size: number;
  risk_percent?: number | null;
  opened_at: string;
  trader_notes?: string | null;
}

export interface JournalEntryUpdate {
  exit_price?: number | null;
  closed_at?: string | null;
  outcome?: TradeOutcome | null;
  profit_loss?: number | null;
  profit_loss_percent?: number | null;
  r_multiple?: number | null;
  ai_summary?: string | null;
  trader_notes?: string | null;
}

export interface ScreenshotAnalysis {
  id: number;
  created_at: string;
  updated_at: string;
  journal_entry_id: number | null;
  file_path: string;
  symbol_hint: string | null;
  detected_trend: string | null;
  detected_support: number[];
  detected_resistance: number[];
  suggested_entry: number | null;
  suggested_stop_loss: number | null;
  suggested_take_profit: number | null;
  mistakes: string[];
  risk_notes: string | null;
  full_report: string;
}

export interface WinRateReport {
  total_trades: number;
  wins: number;
  losses: number;
  breakevens: number;
  win_rate_percent: number;
  average_r_multiple: number | null;
  total_profit_loss: number;
}

export interface PeriodReport {
  period_start: string;
  period_end: string;
  trades: JournalEntry[];
  win_rate: WinRateReport;
  net_profit_loss: number;
  best_trade: JournalEntry | null;
  worst_trade: JournalEntry | null;
}
