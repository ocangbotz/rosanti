import { Send, Trash2 } from "lucide-react";
import { useState } from "react";

import { createSubscriber, listSubscribers, removeSubscriber, sendTestMessage, updatePreferences } from "@/api/telegram";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState, Spinner } from "@/components/ui/Spinner";
import { extractErrorMessage } from "@/lib/apiClient";
import { useApi } from "@/lib/useApi";
import type { TelegramSubscriber } from "@/types";

const PREFERENCE_LABELS: { key: keyof TelegramSubscriber; label: string }[] = [
  { key: "notify_new_setup", label: "New setup" },
  { key: "notify_trade_opened", label: "Trade opened" },
  { key: "notify_trade_closed", label: "Trade closed" },
  { key: "notify_sl_tp_hit", label: "SL/TP hit" },
  { key: "notify_high_impact_news", label: "High-impact news" },
  { key: "notify_daily_summary", label: "Daily summary" },
];

export function TelegramPage() {
  const subscribers = useApi(listSubscribers, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-ink-primary">Telegram Alerts</h1>
        <p className="text-sm text-ink-muted">
          Trade opened/closed, SL/TP hits, new setups, high-impact news, and the daily summary — all
          pushed to Telegram.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>How to connect</CardTitle>
        </CardHeader>
        <CardBody className="space-y-1 text-sm text-ink-secondary">
          <p>1. Message your bot on Telegram and send /start — this registers your chat automatically.</p>
          <p>2. Or add your chat ID manually below (find it via @userinfobot on Telegram).</p>
          <p>3. Toggle which alert categories you want per chat.</p>
        </CardBody>
      </Card>

      <AddSubscriberForm onAdded={subscribers.refetch} />

      <Card>
        <CardHeader>
          <CardTitle>Subscribers</CardTitle>
        </CardHeader>
        <CardBody className="p-0">
          {subscribers.loading ? (
            <LoadingState />
          ) : subscribers.error ? (
            <ErrorState message={subscribers.error} onRetry={subscribers.refetch} />
          ) : !subscribers.data || subscribers.data.length === 0 ? (
            <EmptyState
              title="No subscribers yet"
              description="Send /start to your bot, or add a chat ID above."
            />
          ) : (
            <ul className="divide-y divide-border">
              {subscribers.data.map((sub) => (
                <SubscriberRow key={sub.chat_id} subscriber={sub} onChanged={subscribers.refetch} />
              ))}
            </ul>
          )}
        </CardBody>
      </Card>
    </div>
  );
}

function AddSubscriberForm({ onAdded }: { onAdded: () => void }) {
  const [chatId, setChatId] = useState("");
  const [username, setUsername] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleAdd() {
    if (!chatId.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await createSubscriber({ chat_id: chatId.trim(), username: username.trim() || undefined });
      setChatId("");
      setUsername("");
      onAdded();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <CardBody className="flex flex-wrap items-center gap-3">
        <input
          value={chatId}
          onChange={(e) => setChatId(e.target.value)}
          placeholder="Chat ID"
          className="w-40 rounded-lg border border-border bg-surface-raised px-3 py-2 text-sm text-ink-primary outline-none focus:border-accent"
        />
        <input
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder="Username (optional)"
          className="w-48 rounded-lg border border-border bg-surface-raised px-3 py-2 text-sm text-ink-primary outline-none focus:border-accent"
        />
        <Button onClick={handleAdd} disabled={busy}>
          {busy && <Spinner size={14} />}
          Add subscriber
        </Button>
        {error && <span className="text-xs text-status-critical">{error}</span>}
      </CardBody>
    </Card>
  );
}

function SubscriberRow({ subscriber, onChanged }: { subscriber: TelegramSubscriber; onChanged: () => void }) {
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [testSent, setTestSent] = useState(false);

  async function toggle(key: keyof TelegramSubscriber) {
    setBusyKey(key);
    try {
      await updatePreferences(subscriber.chat_id, { [key]: !subscriber[key] } as Record<string, boolean>);
      onChanged();
    } finally {
      setBusyKey(null);
    }
  }

  async function handleRemove() {
    setBusyKey("remove");
    try {
      await removeSubscriber(subscriber.chat_id);
      onChanged();
    } finally {
      setBusyKey(null);
    }
  }

  async function handleTest() {
    setBusyKey("test");
    try {
      await sendTestMessage({
        chat_id: subscriber.chat_id,
        message: "✅ Fathir AI Trading Assistant is connected.",
      });
      setTestSent(true);
      setTimeout(() => setTestSent(false), 3000);
    } finally {
      setBusyKey(null);
    }
  }

  return (
    <li className="flex flex-wrap items-center justify-between gap-3 px-5 py-4">
      <div>
        <p className="text-sm font-medium text-ink-primary">
          {subscriber.username ? `@${subscriber.username}` : subscriber.chat_id}
        </p>
        <p className="text-xs text-ink-muted">Chat ID: {subscriber.chat_id}</p>
      </div>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        {PREFERENCE_LABELS.map(({ key, label }) => (
          <label key={key} className="flex items-center gap-1.5 text-xs text-ink-secondary">
            <input
              type="checkbox"
              checked={Boolean(subscriber[key])}
              onChange={() => toggle(key)}
              disabled={busyKey === key}
              className="accent-accent"
            />
            {label}
          </label>
        ))}
      </div>

      <div className="flex items-center gap-2">
        <Button variant="secondary" size="sm" onClick={handleTest} disabled={busyKey === "test"}>
          {busyKey === "test" ? <Spinner size={14} /> : <Send size={14} />}
          {testSent ? "Sent!" : "Test"}
        </Button>
        <button
          onClick={handleRemove}
          disabled={busyKey === "remove"}
          className="text-ink-muted transition-colors hover:text-status-critical"
        >
          <Trash2 size={15} />
        </button>
      </div>
    </li>
  );
}
