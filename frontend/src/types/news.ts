import type { NewsImpact } from "./common";

export interface NewsEvent {
  id: number;
  created_at: string;
  updated_at: string;
  title: string;
  country: string;
  currency: string | null;
  impact: NewsImpact;
  event_time: string;
  forecast: string | null;
  previous: string | null;
  actual: string | null;
  source: string;
}

export interface NewsWarning {
  id: number;
  created_at: string;
  updated_at: string;
  title: string;
  currency: string | null;
  impact: NewsImpact;
  event_time: string;
  minutes_until: number;
}

export interface NewsCheckResponse {
  has_high_impact_soon: boolean;
  lookahead_minutes: number;
  events: NewsWarning[];
}
