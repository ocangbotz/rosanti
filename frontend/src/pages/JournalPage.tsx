import { Plus, Trash2, X } from "lucide-react";
import { useState } from "react";

import { createEntry, deleteEntry, listEntries, updateEntry } from "@/api/journal";
import { Badge, DirectionBadge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState, Spinner } from "@/components/ui/Spinner";
import { extractErrorMessage } from "@/lib/apiClient";
import { formatCurrency, formatDateTime, formatPrice } from "@/lib/format";
import { useApi } from "@/lib/useApi";
import type { JournalEntry, TradeDirection, TradeOutcome } from "@/types";

const OUTCOME_TONE: Record<TradeOutcome, "good" | "bear" | "neutral"> = {
  WIN: "good",
  LOSS: "bear",
  BREAKEVEN: "neutral",
  PENDING: "neutral",
};

export function JournalPage() {
  const [page, setPage] = useState(1);
  const [outcomeFilter, setOutcomeFilter] = useState<TradeOutcome | undefined>(undefined);
  const [showNewForm, setShowNewForm] = useState(false);

  const entries = useApi(() => listEntries({ page, page_size: 20, outcome: outcomeFilter }), [
    page,
    outcomeFilter,
  ]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-ink-primary">Trading Journal</h1>
          <p className="text-sm text-ink-muted">Every trade, its AI setup context, and the outcome.</p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={outcomeFilter ?? ""}
            onChange={(e) => {
              setPage(1);
              setOutcomeFilter((e.target.value || undefined) as TradeOutcome | undefined);
            }}
            className="rounded-lg border border-border bg-surface-raised px-3 py-2 text-sm text-ink-primary outline-none focus:border-accent"
          >
            <option value="">All outcomes</option>
            <option value="PENDING">Pending</option>
            <option value="WIN">Win</option>
            <option value="LOSS">Loss</option>
            <option value="BREAKEVEN">Breakeven</option>
          </select>
          <Button onClick={() => setShowNewForm((v) => !v)}>
            <Plus size={16} />
            New Trade
          </Button>
        </div>
      </div>

      {showNewForm && (
        <NewEntryForm
          onCreated={() => {
            setShowNewForm(false);
            entries.refetch();
          }}
          onCancel={() => setShowNewForm(false)}
        />
      )}

      <Card>
        <CardBody className="p-0">
          {entries.loading && !entries.data ? (
            <LoadingState />
          ) : entries.error ? (
            <ErrorState message={entries.error} onRetry={entries.refetch} />
          ) : !entries.data || entries.data.items.length === 0 ? (
            <EmptyState
              title="No journal entries"
              description="Log a trade manually, or take one of your generated setups and record it here."
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-ink-muted">
                    <th className="px-4 py-3">Symbol</th>
                    <th className="px-4 py-3">Direction</th>
                    <th className="px-4 py-3">Entry</th>
                    <th className="px-4 py-3">SL / TP</th>
                    <th className="px-4 py-3">Lot</th>
                    <th className="px-4 py-3">Outcome</th>
                    <th className="px-4 py-3">P&amp;L</th>
                    <th className="px-4 py-3">Opened</th>
                    <th className="px-4 py-3" />
                  </tr>
                </thead>
                <tbody>
                  {entries.data.items.map((entry) => (
                    <EntryRow key={entry.id} entry={entry} onChanged={entries.refetch} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardBody>
      </Card>

      {entries.data && entries.data.total > entries.data.page_size && (
        <div className="flex items-center justify-center gap-3">
          <Button variant="secondary" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
            Previous
          </Button>
          <span className="text-sm text-ink-muted">Page {page}</span>
          <Button
            variant="secondary"
            size="sm"
            disabled={page * entries.data.page_size >= entries.data.total}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </Button>
        </div>
      )}
    </div>
  );
}

function EntryRow({ entry, onChanged }: { entry: JournalEntry; onChanged: () => void }) {
  const [closing, setClosing] = useState(false);
  const [exitPrice, setExitPrice] = useState("");
  const [profitLoss, setProfitLoss] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleClose() {
    if (!exitPrice || !profitLoss) return;
    setBusy(true);
    setError(null);
    try {
      await updateEntry(entry.id, {
        exit_price: Number(exitPrice),
        profit_loss: Number(profitLoss),
        closed_at: new Date().toISOString(),
      });
      setClosing(false);
      onChanged();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete() {
    setBusy(true);
    try {
      await deleteEntry(entry.id);
      onChanged();
    } catch (err) {
      setError(extractErrorMessage(err));
      setBusy(false);
    }
  }

  const digits = entry.symbol.toUpperCase().includes("JPY") ? 3 : 5;

  return (
    <>
      <tr className="border-b border-border last:border-0 hover:bg-surface-raised/40">
        <td className="px-4 py-3 font-medium text-ink-primary">{entry.symbol}</td>
        <td className="px-4 py-3">
          <DirectionBadge direction={entry.direction as TradeDirection} />
        </td>
        <td className="px-4 py-3 tabular-nums text-ink-secondary">{formatPrice(entry.entry_price, digits)}</td>
        <td className="px-4 py-3 tabular-nums text-ink-secondary">
          {formatPrice(entry.stop_loss, digits)} / {formatPrice(entry.take_profit, digits)}
        </td>
        <td className="px-4 py-3 tabular-nums text-ink-secondary">{entry.lot_size}</td>
        <td className="px-4 py-3">
          <Badge tone={OUTCOME_TONE[entry.outcome]}>{entry.outcome}</Badge>
        </td>
        <td className="px-4 py-3 tabular-nums">
          {entry.profit_loss !== null ? (
            <span className={entry.profit_loss >= 0 ? "text-delta-good" : "text-delta-bad"}>
              {formatCurrency(entry.profit_loss)}
            </span>
          ) : (
            <span className="text-ink-muted">—</span>
          )}
        </td>
        <td className="px-4 py-3 text-ink-muted">{formatDateTime(entry.opened_at)}</td>
        <td className="px-4 py-3 text-right">
          <div className="flex items-center justify-end gap-2">
            {entry.outcome === "PENDING" && (
              <Button variant="secondary" size="sm" onClick={() => setClosing((v) => !v)} disabled={busy}>
                Close
              </Button>
            )}
            <button
              onClick={handleDelete}
              disabled={busy}
              className="text-ink-muted transition-colors hover:text-status-critical"
              title="Delete entry"
            >
              <Trash2 size={15} />
            </button>
          </div>
        </td>
      </tr>
      {closing && (
        <tr className="border-b border-border bg-surface-raised/30">
          <td colSpan={9} className="px-4 py-3">
            <div className="flex flex-wrap items-center gap-3">
              <input
                value={exitPrice}
                onChange={(e) => setExitPrice(e.target.value)}
                placeholder="Exit price"
                type="number"
                step="any"
                className="w-32 rounded-lg border border-border bg-surface-card px-3 py-1.5 text-sm text-ink-primary outline-none focus:border-accent"
              />
              <input
                value={profitLoss}
                onChange={(e) => setProfitLoss(e.target.value)}
                placeholder="Profit/loss"
                type="number"
                step="any"
                className="w-32 rounded-lg border border-border bg-surface-card px-3 py-1.5 text-sm text-ink-primary outline-none focus:border-accent"
              />
              <Button size="sm" onClick={handleClose} disabled={busy}>
                {busy && <Spinner size={14} />}
                Confirm close
              </Button>
              {error && <span className="text-xs text-status-critical">{error}</span>}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

function NewEntryForm({ onCreated, onCancel }: { onCreated: () => void; onCancel: () => void }) {
  const [symbol, setSymbol] = useState("EURUSD");
  const [direction, setDirection] = useState<TradeDirection>("BUY");
  const [entryPrice, setEntryPrice] = useState("");
  const [stopLoss, setStopLoss] = useState("");
  const [takeProfit, setTakeProfit] = useState("");
  const [lotSize, setLotSize] = useState("0.10");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    if (!entryPrice || !stopLoss || !takeProfit || !lotSize) {
      setError("All price fields are required.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await createEntry({
        symbol: symbol.toUpperCase(),
        direction,
        entry_price: Number(entryPrice),
        stop_loss: Number(stopLoss),
        take_profit: Number(takeProfit),
        lot_size: Number(lotSize),
        opened_at: new Date().toISOString(),
      });
      onCreated();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <CardBody className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-ink-primary">Log a new trade</h3>
          <button onClick={onCancel} className="text-ink-muted hover:text-ink-primary">
            <X size={16} />
          </button>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <input
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            placeholder="Symbol"
            className="w-28 rounded-lg border border-border bg-surface-raised px-3 py-2 text-sm uppercase text-ink-primary outline-none focus:border-accent"
          />
          <select
            value={direction}
            onChange={(e) => setDirection(e.target.value as TradeDirection)}
            className="rounded-lg border border-border bg-surface-raised px-3 py-2 text-sm text-ink-primary outline-none focus:border-accent"
          >
            <option value="BUY">BUY</option>
            <option value="SELL">SELL</option>
          </select>
          <input
            value={entryPrice}
            onChange={(e) => setEntryPrice(e.target.value)}
            placeholder="Entry price"
            type="number"
            step="any"
            className="w-32 rounded-lg border border-border bg-surface-raised px-3 py-2 text-sm text-ink-primary outline-none focus:border-accent"
          />
          <input
            value={stopLoss}
            onChange={(e) => setStopLoss(e.target.value)}
            placeholder="Stop loss"
            type="number"
            step="any"
            className="w-32 rounded-lg border border-border bg-surface-raised px-3 py-2 text-sm text-ink-primary outline-none focus:border-accent"
          />
          <input
            value={takeProfit}
            onChange={(e) => setTakeProfit(e.target.value)}
            placeholder="Take profit"
            type="number"
            step="any"
            className="w-32 rounded-lg border border-border bg-surface-raised px-3 py-2 text-sm text-ink-primary outline-none focus:border-accent"
          />
          <input
            value={lotSize}
            onChange={(e) => setLotSize(e.target.value)}
            placeholder="Lot size"
            type="number"
            step="any"
            className="w-28 rounded-lg border border-border bg-surface-raised px-3 py-2 text-sm text-ink-primary outline-none focus:border-accent"
          />
          <Button onClick={handleSubmit} disabled={busy}>
            {busy && <Spinner size={14} />}
            Save
          </Button>
        </div>
        {error && <p className="text-xs text-status-critical">{error}</p>}
      </CardBody>
    </Card>
  );
}
