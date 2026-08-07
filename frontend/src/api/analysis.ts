import { apiClient } from "@/lib/apiClient";
import type { MarketAnalysis, NarrativeResponse, Timeframe } from "@/types";

export async function getMarketAnalysis(
  symbol: string,
  timeframe: Timeframe = "H1",
  count = 300,
): Promise<MarketAnalysis> {
  const { data } = await apiClient.get<MarketAnalysis>("/api/v1/analysis", {
    params: { symbol, timeframe, count },
  });
  return data;
}

export async function getMarketNarrative(
  symbol: string,
  timeframe: Timeframe = "H1",
  count = 300,
): Promise<NarrativeResponse> {
  const { data } = await apiClient.get<NarrativeResponse>("/api/v1/analysis/narrative", {
    params: { symbol, timeframe, count },
  });
  return data;
}
