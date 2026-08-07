import { apiClient } from "@/lib/apiClient";
import type {
  BreakevenRequest,
  BreakevenResponse,
  DailyLimitCheckResponse,
  DrawdownInfo,
  LotSizeRequest,
  LotSizeResponse,
  RiskSettings,
  RiskSettingsUpdate,
} from "@/types";

export async function getRiskSettings(accountId?: number | null): Promise<RiskSettings> {
  const { data } = await apiClient.get<RiskSettings>("/api/v1/risk/settings", {
    params: accountId ? { account_id: accountId } : {},
  });
  return data;
}

export async function updateRiskSettings(
  update: RiskSettingsUpdate,
  accountId?: number | null,
): Promise<RiskSettings> {
  const { data } = await apiClient.put<RiskSettings>("/api/v1/risk/settings", update, {
    params: accountId ? { account_id: accountId } : {},
  });
  return data;
}

export async function calculateLotSize(request: LotSizeRequest): Promise<LotSizeResponse> {
  const { data } = await apiClient.post<LotSizeResponse>("/api/v1/risk/lot-size", request);
  return data;
}

export async function calculateBreakeven(request: BreakevenRequest): Promise<BreakevenResponse> {
  const { data } = await apiClient.post<BreakevenResponse>("/api/v1/risk/breakeven", request);
  return data;
}

export async function getDailyLimits(accountId: number): Promise<DailyLimitCheckResponse> {
  const { data } = await apiClient.get<DailyLimitCheckResponse>("/api/v1/risk/daily-limits", {
    params: { account_id: accountId },
  });
  return data;
}

export async function getDrawdown(accountId: number): Promise<DrawdownInfo> {
  const { data } = await apiClient.get<DrawdownInfo>("/api/v1/risk/drawdown", {
    params: { account_id: accountId },
  });
  return data;
}
