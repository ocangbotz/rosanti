import { apiClient } from "@/lib/apiClient";
import type {
  TelegramPreferencesUpdate,
  TelegramSubscriber,
  TelegramSubscriberCreate,
  TelegramTestMessageRequest,
} from "@/types";

export async function listSubscribers(): Promise<TelegramSubscriber[]> {
  const { data } = await apiClient.get<TelegramSubscriber[]>("/api/v1/telegram/subscribers");
  return data;
}

export async function createSubscriber(data: TelegramSubscriberCreate): Promise<TelegramSubscriber> {
  const response = await apiClient.post<TelegramSubscriber>("/api/v1/telegram/subscribers", data);
  return response.data;
}

export async function updatePreferences(
  chatId: string,
  update: TelegramPreferencesUpdate,
): Promise<TelegramSubscriber> {
  const { data } = await apiClient.patch<TelegramSubscriber>(
    `/api/v1/telegram/subscribers/${chatId}`,
    update,
  );
  return data;
}

export async function removeSubscriber(chatId: string): Promise<void> {
  await apiClient.delete(`/api/v1/telegram/subscribers/${chatId}`);
}

export async function sendTestMessage(
  request: TelegramTestMessageRequest,
): Promise<{ sent: string[]; failed: unknown[] }> {
  const { data } = await apiClient.post("/api/v1/telegram/test-message", request);
  return data;
}
