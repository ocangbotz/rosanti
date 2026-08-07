export interface TelegramSubscriber {
  id: number;
  created_at: string;
  updated_at: string;
  chat_id: string;
  username: string | null;
  is_active: boolean;
  notify_trade_opened: boolean;
  notify_trade_closed: boolean;
  notify_sl_tp_hit: boolean;
  notify_high_impact_news: boolean;
  notify_daily_summary: boolean;
  notify_new_setup: boolean;
}

export interface TelegramSubscriberCreate {
  chat_id: string;
  username?: string | null;
}

export interface TelegramPreferencesUpdate {
  is_active?: boolean;
  notify_trade_opened?: boolean;
  notify_trade_closed?: boolean;
  notify_sl_tp_hit?: boolean;
  notify_high_impact_news?: boolean;
  notify_daily_summary?: boolean;
  notify_new_setup?: boolean;
}

export interface TelegramTestMessageRequest {
  chat_id?: string | null;
  message: string;
}
