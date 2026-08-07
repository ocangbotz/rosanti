import { useEffect, useState } from "react";

import { createAccount, listAccounts } from "@/api/account";
import { calculateBreakeven, calculateLotSize, getRiskSettings, updateRiskSettings } from "@/api/risk";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState, Spinner } from "@/components/ui/Spinner";
import { extractErrorMessage } from "@/lib/apiClient";
import { useApi } from "@/lib/useApi";
import { useAppStore } from "@/store/useAppStore";
import type { BreakevenResponse, LotSizeResponse } from "@/types";

export function SettingsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-ink-primary">Settings</h1>
        <p className="text-sm text-ink-muted">Risk limits, calculators, broker accounts, and API access.</p>
      </div>

      <RiskSettingsCard />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <LotSizeCalculatorCard />
        <BreakevenCalculatorCard />
      </div>

      <BrokerAccountsCard />
      <ApiKeyCard />
    </div>
  );
}

function RiskSettingsCard() {
  const { accountId } = useAppStore();
  const settings = useApi(() => getRiskSettings(accountId), [accountId]);
  const [form, setForm] = useState({
    risk_percent: "",
    max_daily_loss_percent: "",
    max_trades_per_day: "",
    max_drawdown_percent: "",
    breakeven_trigger_r: "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (settings.data) {
      setForm({
        risk_percent: String(settings.data.risk_percent),
        max_daily_loss_percent: String(settings.data.max_daily_loss_percent),
        max_trades_per_day: String(settings.data.max_trades_per_day),
        max_drawdown_percent: String(settings.data.max_drawdown_percent),
        breakeven_trigger_r: String(settings.data.breakeven_trigger_r),
      });
    }
  }, [settings.data]);

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      await updateRiskSettings(
        {
          risk_percent: Number(form.risk_percent),
          max_daily_loss_percent: Number(form.max_daily_loss_percent),
          max_trades_per_day: Number(form.max_trades_per_day),
          max_drawdown_percent: Number(form.max_drawdown_percent),
          breakeven_trigger_r: Number(form.breakeven_trigger_r),
        },
        accountId,
      );
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Risk Management</CardTitle>
      </CardHeader>
      <CardBody>
        {settings.loading ? (
          <LoadingState />
        ) : settings.error ? (
          <ErrorState message={settings.error} onRetry={settings.refetch} />
        ) : (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
            <Field
              label="Risk per trade (%)"
              value={form.risk_percent}
              onChange={(v) => setForm((f) => ({ ...f, risk_percent: v }))}
            />
            <Field
              label="Max daily loss (%)"
              value={form.max_daily_loss_percent}
              onChange={(v) => setForm((f) => ({ ...f, max_daily_loss_percent: v }))}
            />
            <Field
              label="Max trades/day"
              value={form.max_trades_per_day}
              onChange={(v) => setForm((f) => ({ ...f, max_trades_per_day: v }))}
            />
            <Field
              label="Max drawdown (%)"
              value={form.max_drawdown_percent}
              onChange={(v) => setForm((f) => ({ ...f, max_drawdown_percent: v }))}
            />
            <Field
              label="Breakeven trigger (R)"
              value={form.breakeven_trigger_r}
              onChange={(v) => setForm((f) => ({ ...f, breakeven_trigger_r: v }))}
            />
          </div>
        )}
        <div className="mt-4 flex items-center gap-3">
          <Button onClick={handleSave} disabled={saving || settings.loading}>
            {saving && <Spinner size={14} />}
            Save
          </Button>
          {saved && <Badge tone="good">Saved</Badge>}
          {error && <span className="text-xs text-status-critical">{error}</span>}
        </div>
      </CardBody>
    </Card>
  );
}

function Field({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs text-ink-muted">{label}</span>
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        type="number"
        step="any"
        className="w-full rounded-lg border border-border bg-surface-raised px-3 py-2 text-sm text-ink-primary outline-none focus:border-accent"
      />
    </label>
  );
}

function LotSizeCalculatorCard() {
  const [balance, setBalance] = useState("10000");
  const [riskPercent, setRiskPercent] = useState("1");
  const [entry, setEntry] = useState("1.1000");
  const [stopLoss, setStopLoss] = useState("1.0950");
  const [symbol, setSymbol] = useState("EURUSD");
  const [result, setResult] = useState<LotSizeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleCalculate() {
    setBusy(true);
    setError(null);
    try {
      const response = await calculateLotSize({
        account_balance: Number(balance),
        risk_percent: Number(riskPercent),
        entry_price: Number(entry),
        stop_loss: Number(stopLoss),
        symbol,
      });
      setResult(response);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Lot Size Calculator</CardTitle>
      </CardHeader>
      <CardBody className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <Field label="Account balance" value={balance} onChange={setBalance} />
          <Field label="Risk %" value={riskPercent} onChange={setRiskPercent} />
          <Field label="Entry price" value={entry} onChange={setEntry} />
          <Field label="Stop loss" value={stopLoss} onChange={setStopLoss} />
        </div>
        <label className="block">
          <span className="mb-1 block text-xs text-ink-muted">Symbol</span>
          <input
            value={symbol}
            onChange={(e) => setSymbol(e.target.value.toUpperCase())}
            className="w-full rounded-lg border border-border bg-surface-raised px-3 py-2 text-sm text-ink-primary outline-none focus:border-accent"
          />
        </label>
        <Button onClick={handleCalculate} disabled={busy}>
          {busy && <Spinner size={14} />}
          Calculate
        </Button>
        {error && <p className="text-xs text-status-critical">{error}</p>}
        {result && (
          <div className="rounded-lg border border-border bg-surface-raised p-3 text-sm">
            <p className="text-lg font-semibold tabular-nums text-ink-primary">{result.lot_size} lots</p>
            <p className="text-ink-muted">
              Risking {result.risk_amount.toFixed(2)} over {result.stop_loss_pips.toFixed(1)} pips
            </p>
          </div>
        )}
      </CardBody>
    </Card>
  );
}

function BreakevenCalculatorCard() {
  const [entry, setEntry] = useState("1.1000");
  const [stopLoss, setStopLoss] = useState("1.0950");
  const [currentPrice, setCurrentPrice] = useState("1.1050");
  const [direction, setDirection] = useState<"BUY" | "SELL">("BUY");
  const [triggerR, setTriggerR] = useState("1");
  const [result, setResult] = useState<BreakevenResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleCalculate() {
    setBusy(true);
    setError(null);
    try {
      const response = await calculateBreakeven({
        entry_price: Number(entry),
        stop_loss: Number(stopLoss),
        current_price: Number(currentPrice),
        direction,
        trigger_r: Number(triggerR),
      });
      setResult(response);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Breakeven Calculator</CardTitle>
      </CardHeader>
      <CardBody className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <Field label="Entry price" value={entry} onChange={setEntry} />
          <Field label="Stop loss" value={stopLoss} onChange={setStopLoss} />
          <Field label="Current price" value={currentPrice} onChange={setCurrentPrice} />
          <Field label="Trigger (R)" value={triggerR} onChange={setTriggerR} />
        </div>
        <label className="block">
          <span className="mb-1 block text-xs text-ink-muted">Direction</span>
          <select
            value={direction}
            onChange={(e) => setDirection(e.target.value as "BUY" | "SELL")}
            className="w-full rounded-lg border border-border bg-surface-raised px-3 py-2 text-sm text-ink-primary outline-none focus:border-accent"
          >
            <option value="BUY">BUY</option>
            <option value="SELL">SELL</option>
          </select>
        </label>
        <Button onClick={handleCalculate} disabled={busy}>
          {busy && <Spinner size={14} />}
          Calculate
        </Button>
        {error && <p className="text-xs text-status-critical">{error}</p>}
        {result && (
          <div className="rounded-lg border border-border bg-surface-raised p-3 text-sm">
            <p className="text-lg font-semibold tabular-nums text-ink-primary">
              {result.current_r_multiple.toFixed(2)}R
            </p>
            <p className={result.breakeven_reached ? "text-delta-good" : "text-ink-muted"}>
              {result.breakeven_reached
                ? `Breakeven reached — move stop to ${result.suggested_new_stop_loss}`
                : "Not yet at breakeven trigger"}
            </p>
          </div>
        )}
      </CardBody>
    </Card>
  );
}

function BrokerAccountsCard() {
  const accounts = useApi(listAccounts, []);
  const [showForm, setShowForm] = useState(false);
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [server, setServer] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleAdd() {
    setBusy(true);
    setError(null);
    try {
      await createAccount({ login: Number(login), password, server });
      setShowForm(false);
      setLogin("");
      setPassword("");
      setServer("");
      accounts.refetch();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Broker Accounts</CardTitle>
        <Button variant="secondary" size="sm" onClick={() => setShowForm((v) => !v)}>
          Add account
        </Button>
      </CardHeader>
      <CardBody className="space-y-4">
        {showForm && (
          <div className="flex flex-wrap items-center gap-3 rounded-lg border border-border bg-surface-raised p-3">
            <input
              value={login}
              onChange={(e) => setLogin(e.target.value)}
              placeholder="Login"
              type="number"
              className="w-32 rounded-lg border border-border bg-surface-card px-3 py-2 text-sm text-ink-primary outline-none focus:border-accent"
            />
            <input
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Password"
              type="password"
              className="w-40 rounded-lg border border-border bg-surface-card px-3 py-2 text-sm text-ink-primary outline-none focus:border-accent"
            />
            <input
              value={server}
              onChange={(e) => setServer(e.target.value)}
              placeholder="Server"
              className="w-44 rounded-lg border border-border bg-surface-card px-3 py-2 text-sm text-ink-primary outline-none focus:border-accent"
            />
            <Button size="sm" onClick={handleAdd} disabled={busy}>
              {busy && <Spinner size={14} />}
              Save
            </Button>
            {error && <span className="text-xs text-status-critical">{error}</span>}
          </div>
        )}

        {accounts.loading ? (
          <LoadingState />
        ) : accounts.error ? (
          <ErrorState message={accounts.error} onRetry={accounts.refetch} />
        ) : !accounts.data || accounts.data.length === 0 ? (
          <p className="text-sm text-ink-muted">
            No saved accounts yet. In mock mode the scheduler creates one automatically once it starts
            polling.
          </p>
        ) : (
          <ul className="divide-y divide-border">
            {accounts.data.map((account) => (
              <li key={account.id} className="flex items-center justify-between py-2 text-sm">
                <span className="text-ink-primary">
                  {account.login} · {account.server}
                </span>
                <Badge tone={account.is_active ? "good" : "neutral"}>
                  {account.is_active ? "Active" : "Inactive"}
                </Badge>
              </li>
            ))}
          </ul>
        )}
      </CardBody>
    </Card>
  );
}

function ApiKeyCard() {
  const { apiKey, setApiKey } = useAppStore();
  const [value, setValue] = useState(apiKey);
  const [saved, setSaved] = useState(false);

  return (
    <Card>
      <CardHeader>
        <CardTitle>API Access</CardTitle>
      </CardHeader>
      <CardBody className="space-y-3">
        <p className="text-sm text-ink-muted">
          Only needed once the backend is deployed with a real <code>API_KEY</code> set (see
          backend/.env.example). Local development runs with auth disabled by default.
        </p>
        <div className="flex items-center gap-3">
          <input
            value={value}
            onChange={(e) => setValue(e.target.value)}
            type="password"
            placeholder="X-API-Key"
            className="w-64 rounded-lg border border-border bg-surface-raised px-3 py-2 text-sm text-ink-primary outline-none focus:border-accent"
          />
          <Button
            variant="secondary"
            onClick={() => {
              setApiKey(value);
              setSaved(true);
              setTimeout(() => setSaved(false), 2000);
            }}
          >
            Save
          </Button>
          {saved && <Badge tone="good">Saved</Badge>}
        </div>
      </CardBody>
    </Card>
  );
}
