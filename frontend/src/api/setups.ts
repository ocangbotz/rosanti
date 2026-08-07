import { apiClient } from "@/lib/apiClient";
import type { GenerateSetupRequest, Page, SetupStatus, TradeSetup, TradeSetupSummary } from "@/types";

export async function generateSetup(request: GenerateSetupRequest): Promise<TradeSetup> {
  const { data } = await apiClient.post<TradeSetup>("/api/v1/setups/generate", request);
  return data;
}

export async function listSetups(params: {
  symbol?: string;
  status?: SetupStatus;
  page?: number;
  page_size?: number;
}): Promise<Page<TradeSetupSummary>> {
  const { data } = await apiClient.get<Page<TradeSetupSummary>>("/api/v1/setups", { params });
  return data;
}

export async function getSetup(id: number): Promise<TradeSetup> {
  const { data } = await apiClient.get<TradeSetup>(`/api/v1/setups/${id}`);
  return data;
}

export async function updateSetupStatus(id: number, newStatus: SetupStatus): Promise<TradeSetup> {
  const { data } = await apiClient.patch<TradeSetup>(`/api/v1/setups/${id}/status`, null, {
    params: { new_status: newStatus },
  });
  return data;
}
