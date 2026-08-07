import { apiClient } from "@/lib/apiClient";
import type {
  OHLCResponse,
  OrderRequest,
  OrderResult,
  PositionInfo,
  SymbolInfo,
  Timeframe,
} from "@/types";

export async function getOhlc(
  symbol: string,
  timeframe: Timeframe = "H1",
  count = 300,
): Promise<OHLCResponse> {
  const { data } = await apiClient.get<OHLCResponse>("/api/v1/market/ohlc", {
    params: { symbol, timeframe, count },
  });
  return data;
}

export async function getSymbolInfo(symbol: string): Promise<SymbolInfo> {
  const { data } = await apiClient.get<SymbolInfo>("/api/v1/market/symbol-info", {
    params: { symbol },
  });
  return data;
}

export async function getPositions(): Promise<PositionInfo[]> {
  const { data } = await apiClient.get<PositionInfo[]>("/api/v1/market/positions");
  return data;
}

export async function placeOrder(request: OrderRequest): Promise<OrderResult> {
  const { data } = await apiClient.post<OrderResult>("/api/v1/market/orders", request);
  return data;
}

export async function closePosition(ticket: number): Promise<OrderResult> {
  const { data } = await apiClient.delete<OrderResult>(`/api/v1/market/positions/${ticket}`);
  return data;
}
