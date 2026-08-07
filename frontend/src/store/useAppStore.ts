import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { Timeframe } from "@/types";

export type Theme = "dark" | "light";

interface AppState {
  theme: Theme;
  toggleTheme: () => void;

  selectedSymbol: string;
  setSelectedSymbol: (symbol: string) => void;

  selectedTimeframe: Timeframe;
  setSelectedTimeframe: (timeframe: Timeframe) => void;

  accountId: number | null;
  setAccountId: (id: number | null) => void;

  apiKey: string;
  setApiKey: (key: string) => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      theme: "dark",
      toggleTheme: () => {
        const next = get().theme === "dark" ? "light" : "dark";
        document.documentElement.dataset.theme = next;
        set({ theme: next });
      },

      selectedSymbol: "EURUSD",
      setSelectedSymbol: (symbol) => set({ selectedSymbol: symbol.toUpperCase() }),

      selectedTimeframe: "H1",
      setSelectedTimeframe: (timeframe) => set({ selectedTimeframe: timeframe }),

      accountId: null,
      setAccountId: (id) => set({ accountId: id }),

      apiKey: "",
      setApiKey: (key) => {
        localStorage.setItem("fathir_api_key", key);
        set({ apiKey: key });
      },
    }),
    {
      name: "fathir-app-store",
      partialize: (state) => ({
        theme: state.theme,
        selectedSymbol: state.selectedSymbol,
        selectedTimeframe: state.selectedTimeframe,
        accountId: state.accountId,
      }),
    },
  ),
);

/** Applies the persisted theme to <html data-theme> on initial load. */
export function initializeTheme(): void {
  const theme = useAppStore.getState().theme;
  document.documentElement.dataset.theme = theme;
}
