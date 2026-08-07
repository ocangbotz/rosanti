import { apiClient } from "@/lib/apiClient";
import type { AppSetting, AppSettingUpsert } from "@/types";

export async function listSettings(): Promise<AppSetting[]> {
  const { data } = await apiClient.get<AppSetting[]>("/api/v1/settings");
  return data;
}

export async function getSetting(key: string): Promise<AppSetting> {
  const { data } = await apiClient.get<AppSetting>(`/api/v1/settings/${key}`);
  return data;
}

export async function upsertSetting(key: string, payload: AppSettingUpsert): Promise<AppSetting> {
  const { data } = await apiClient.put<AppSetting>(`/api/v1/settings/${key}`, payload);
  return data;
}
