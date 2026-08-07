export interface AppSetting {
  id: number;
  created_at: string;
  updated_at: string;
  key: string;
  value: Record<string, unknown>;
}

export interface AppSettingUpsert {
  key: string;
  value: Record<string, unknown>;
}
