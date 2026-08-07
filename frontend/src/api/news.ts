import { apiClient } from "@/lib/apiClient";
import type { NewsCheckResponse, NewsEvent } from "@/types";

export async function getUpcomingNews(lookaheadMinutes = 60): Promise<NewsCheckResponse> {
  const { data } = await apiClient.get<NewsCheckResponse>("/api/v1/news/upcoming", {
    params: { lookahead_minutes: lookaheadMinutes },
  });
  return data;
}

export async function refreshCalendar(): Promise<NewsEvent[]> {
  const { data } = await apiClient.post<NewsEvent[]>("/api/v1/news/refresh");
  return data;
}

export async function listNewsEvents(limit = 100): Promise<NewsEvent[]> {
  const { data } = await apiClient.get<NewsEvent[]>("/api/v1/news/events", { params: { limit } });
  return data;
}
