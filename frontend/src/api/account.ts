import { apiClient } from "@/lib/apiClient";
import type { AccountSnapshot, BrokerAccount, BrokerAccountCreate, LiveAccountInfo } from "@/types";

export async function createAccount(data: BrokerAccountCreate): Promise<BrokerAccount> {
  const response = await apiClient.post<BrokerAccount>("/api/v1/accounts", data);
  return response.data;
}

export async function listAccounts(): Promise<BrokerAccount[]> {
  const { data } = await apiClient.get<BrokerAccount[]>("/api/v1/accounts");
  return data;
}

export async function getAccount(id: number): Promise<BrokerAccount> {
  const { data } = await apiClient.get<BrokerAccount>(`/api/v1/accounts/${id}`);
  return data;
}

export async function getLiveAccountInfo(): Promise<LiveAccountInfo> {
  const { data } = await apiClient.get<LiveAccountInfo>("/api/v1/accounts/live");
  return data;
}

export async function getAccountSnapshots(id: number, limit = 200): Promise<AccountSnapshot[]> {
  const { data } = await apiClient.get<AccountSnapshot[]>(`/api/v1/accounts/${id}/snapshots`, {
    params: { limit },
  });
  return data;
}
