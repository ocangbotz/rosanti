import { apiClient } from "@/lib/apiClient";
import type { ScreenshotAnalysis } from "@/types";

export async function analyzeScreenshot(
  file: File,
  symbolHint?: string,
  journalEntryId?: number,
): Promise<ScreenshotAnalysis> {
  const formData = new FormData();
  formData.append("file", file);
  if (symbolHint) formData.append("symbol_hint", symbolHint);
  if (journalEntryId) formData.append("journal_entry_id", String(journalEntryId));

  const { data } = await apiClient.post<ScreenshotAnalysis>("/api/v1/screenshot/analyze", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function getScreenshotAnalysis(id: number): Promise<ScreenshotAnalysis> {
  const { data } = await apiClient.get<ScreenshotAnalysis>(`/api/v1/screenshot/${id}`);
  return data;
}
