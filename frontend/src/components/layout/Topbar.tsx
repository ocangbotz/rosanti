import { Moon, Sun } from "lucide-react";
import { useState } from "react";

import { useAppStore } from "@/store/useAppStore";
import { TIMEFRAMES, type Timeframe } from "@/types";

const POPULAR_SYMBOLS = [
  "EURUSD",
  "GBPUSD",
  "USDJPY",
  "USDCHF",
  "AUDUSD",
  "USDCAD",
  "NZDUSD",
  "XAUUSD",
  "BTCUSD",
];

export function Topbar() {
  const { selectedSymbol, setSelectedSymbol, selectedTimeframe, setSelectedTimeframe, theme, toggleTheme } =
    useAppStore();
  const [symbolInput, setSymbolInput] = useState(selectedSymbol);

  function commitSymbol() {
    const trimmed = symbolInput.trim().toUpperCase();
    if (trimmed) setSelectedSymbol(trimmed);
  }

  return (
    <header className="flex h-16 shrink-0 items-center justify-between gap-4 border-b border-border bg-surface-card px-6">
      <div className="flex items-center gap-3">
        <input
          list="symbol-suggestions"
          value={symbolInput}
          onChange={(e) => setSymbolInput(e.target.value)}
          onBlur={commitSymbol}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              commitSymbol();
              e.currentTarget.blur();
            }
          }}
          className="w-32 rounded-lg border border-border bg-surface-raised px-3 py-1.5 text-sm font-semibold uppercase text-ink-primary outline-none focus:border-accent"
          placeholder="EURUSD"
        />
        <datalist id="symbol-suggestions">
          {POPULAR_SYMBOLS.map((s) => (
            <option key={s} value={s} />
          ))}
        </datalist>

        <select
          value={selectedTimeframe}
          onChange={(e) => setSelectedTimeframe(e.target.value as Timeframe)}
          className="rounded-lg border border-border bg-surface-raised px-3 py-1.5 text-sm font-medium text-ink-primary outline-none focus:border-accent"
        >
          {TIMEFRAMES.map((tf) => (
            <option key={tf} value={tf}>
              {tf}
            </option>
          ))}
        </select>
      </div>

      <button
        type="button"
        onClick={toggleTheme}
        className="flex h-9 w-9 items-center justify-center rounded-lg border border-border text-ink-secondary transition-colors hover:bg-surface-raised hover:text-ink-primary"
        title="Toggle theme"
      >
        {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
      </button>
    </header>
  );
}
