import type { TradeDirection } from "./common";

export interface BrokerAccount {
  id: number;
  created_at: string;
  updated_at: string;
  login: number;
  server: string;
  broker_name: string;
  currency: string;
  leverage: number;
  is_active: boolean;
}

export interface BrokerAccountCreate {
  login: number;
  password: string;
  server: string;
  broker_name?: string;
  currency?: string;
  leverage?: number;
}

export interface LiveAccountInfo {
  login: number;
  server: string;
  currency: string;
  leverage: number;
  balance: number;
  equity: number;
  margin: number;
  free_margin: number;
  margin_level: number | null;
  profit: number;
  connected: boolean;
}

export interface AccountSnapshot {
  id: number;
  created_at: string;
  updated_at: string;
  account_id: number;
  balance: number;
  equity: number;
  margin: number;
  free_margin: number;
  margin_level: number | null;
}

export interface SymbolInfo {
  symbol: string;
  bid: number;
  ask: number;
  spread_points: number;
  point: number;
  digits: number;
  contract_size: number;
  volume_min: number;
  volume_max: number;
  volume_step: number;
  pip_size: number;
  pip_value_per_lot: number;
}

export interface PositionInfo {
  ticket: number;
  symbol: string;
  direction: TradeDirection;
  volume: number;
  open_price: number;
  current_price: number;
  stop_loss: number | null;
  take_profit: number | null;
  profit: number;
  swap: number;
  opened_at: string;
}

export interface OrderRequest {
  symbol: string;
  direction: TradeDirection;
  volume: number;
  stop_loss?: number | null;
  take_profit?: number | null;
  comment?: string;
}

export interface OrderResult {
  success: boolean;
  ticket: number | null;
  executed_price: number | null;
  message: string;
}
