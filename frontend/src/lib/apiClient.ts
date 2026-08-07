import axios, { AxiosError } from "axios";

/**
 * Base URL resolution: in dev, an empty base lets Vite's proxy (see
 * vite.config.ts) forward /api/* to the backend, avoiding CORS entirely.
 * In production the built assets are served separately from the API, so
 * VITE_API_BASE_URL must point at the real backend origin.
 */
const baseURL = import.meta.env.VITE_API_BASE_URL || "";

export const apiClient = axios.create({
  baseURL,
  timeout: 30_000,
});

apiClient.interceptors.request.use((config) => {
  const apiKey = import.meta.env.VITE_API_KEY || localStorage.getItem("fathir_api_key");
  if (apiKey) {
    config.headers.set("X-API-Key", apiKey);
  }
  return config;
});

export interface ApiErrorPayload {
  detail?: string;
}

export function extractErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<ApiErrorPayload>;
    const detail = axiosError.response?.data?.detail;
    if (detail) return detail;
    if (axiosError.message) return axiosError.message;
  }
  if (error instanceof Error) return error.message;
  return "An unexpected error occurred.";
}
