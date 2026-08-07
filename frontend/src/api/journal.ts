import { apiClient } from "@/lib/apiClient";
import type {
  JournalEntry,
  JournalEntryCreate,
  JournalEntryUpdate,
  Page,
  PeriodReport,
  TradeOutcome,
  WinRateReport,
} from "@/types";

export async function createEntry(data: JournalEntryCreate): Promise<JournalEntry> {
  const response = await apiClient.post<JournalEntry>("/api/v1/journal/entries", data);
  return response.data;
}

export async function listEntries(params: {
  account_id?: number;
  symbol?: string;
  outcome?: TradeOutcome;
  page?: number;
  page_size?: number;
}): Promise<Page<JournalEntry>> {
  const { data } = await apiClient.get<Page<JournalEntry>>("/api/v1/journal/entries", { params });
  return data;
}

export async function getEntry(id: number): Promise<JournalEntry> {
  const { data } = await apiClient.get<JournalEntry>(`/api/v1/journal/entries/${id}`);
  return data;
}

export async function updateEntry(id: number, update: JournalEntryUpdate): Promise<JournalEntry> {
  const { data } = await apiClient.patch<JournalEntry>(`/api/v1/journal/entries/${id}`, update);
  return data;
}

export async function deleteEntry(id: number): Promise<void> {
  await apiClient.delete(`/api/v1/journal/entries/${id}`);
}

export async function getWinRate(accountId?: number): Promise<WinRateReport> {
  const { data } = await apiClient.get<WinRateReport>("/api/v1/journal/reports/win-rate", {
    params: accountId ? { account_id: accountId } : {},
  });
  return data;
}

export async function getWeeklyReport(accountId?: number): Promise<PeriodReport> {
  const { data } = await apiClient.get<PeriodReport>("/api/v1/journal/reports/weekly", {
    params: accountId ? { account_id: accountId } : {},
  });
  return data;
}

export async function getMonthlyReport(accountId?: number): Promise<PeriodReport> {
  const { data } = await apiClient.get<PeriodReport>("/api/v1/journal/reports/monthly", {
    params: accountId ? { account_id: accountId } : {},
  });
  return data;
}
