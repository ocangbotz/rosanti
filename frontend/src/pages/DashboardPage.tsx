import { AlertTriangle, TrendingUp, Wallet } from "lucide-react";
import { Link } from "react-router-dom";

import { getLiveAccountInfo } from "@/api/account";
import { getWinRate } from "@/api/journal";
import { getUpcomingNews } from "@/api/news";
import { listSetups } from "@/api/setups";
import { Badge, DirectionBadge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { ConfidenceBar } from "@/components/ui/ConfidenceBar";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/Spinner";
import { StatTile } from "@/components/ui/StatTile";
import { formatCurrency, formatDateTime, formatPercent } from "@/lib/format";
import { useApi } from "@/lib/useApi";

export function DashboardPage() {
  const account = useApi(getLiveAccountInfo, []);
  const winRate = useApi(getWinRate, []);
  const news = useApi(() => getUpcomingNews(120), []);
  const setups = useApi(() => listSetups({ page: 1, page_size: 5 }), []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-ink-primary">Dashboard</h1>
          <p className="text-sm text-ink-muted">Live account status and the latest AI-generated setups.</p>
        </div>
        <Link to="/analysis">
          <Button>Analyze a symbol</Button>
        </Link>
      </div>

      {news.data?.has_high_impact_soon && (
        <div className="flex items-center gap-3 rounded-xl border border-status-warning/30 bg-status-warning/10 px-4 py-3">
          <AlertTriangle className="shrink-0 text-status-warning" size={18} />
          <p className="text-sm text-ink-primary">
            High-impact news in the next 2 hours:{" "}
            <span className="font-medium">
              {news.data.events.map((e) => e.title).join(", ")}
            </span>
            . Consider avoiding new positions until after the release.
          </p>
        </div>
      )}

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {account.loading && !account.data ? (
          <div className="col-span-full">
            <LoadingState label="Loading account…" />
          </div>
        ) : account.error ? (
          <div className="col-span-full">
            <ErrorState message={account.error} onRetry={account.refetch} />
          </div>
        ) : (
          account.data && (
            <>
              <StatTile
                label="Balance"
                value={formatCurrency(account.data.balance, account.data.currency)}
                icon={<Wallet size={16} />}
              />
              <StatTile
                label="Equity"
                value={formatCurrency(account.data.equity, account.data.currency)}
                delta={
                  account.data.profit !== 0
                    ? `${account.data.profit > 0 ? "+" : ""}${formatCurrency(account.data.profit, account.data.currency)} floating`
                    : undefined
                }
                deltaTone={account.data.profit > 0 ? "good" : account.data.profit < 0 ? "bad" : "neutral"}
                icon={<TrendingUp size={16} />}
              />
              <StatTile label="Margin used" value={formatCurrency(account.data.margin, account.data.currency)} />
              <StatTile
                label="Free margin"
                value={formatCurrency(account.data.free_margin, account.data.currency)}
              />
            </>
          )
        )}
      </section>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle>Win Rate</CardTitle>
          </CardHeader>
          <CardBody>
            {winRate.loading ? (
              <LoadingState />
            ) : winRate.error ? (
              <ErrorState message={winRate.error} onRetry={winRate.refetch} />
            ) : winRate.data ? (
              <div className="space-y-3">
                <p className="text-3xl font-semibold tabular-nums text-ink-primary">
                  {formatPercent(winRate.data.win_rate_percent, 0)}
                </p>
                <p className="text-sm text-ink-muted">
                  {winRate.data.wins}W / {winRate.data.losses}L / {winRate.data.breakevens}BE (
                  {winRate.data.total_trades} trades)
                </p>
                <p className="text-sm text-ink-secondary">
                  Total P&L:{" "}
                  <span
                    className={winRate.data.total_profit_loss >= 0 ? "text-delta-good" : "text-delta-bad"}
                  >
                    {formatCurrency(winRate.data.total_profit_loss)}
                  </span>
                </p>
              </div>
            ) : null}
          </CardBody>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Latest Trade Setups</CardTitle>
            <Link to="/analysis" className="text-xs font-medium text-accent hover:text-accent-hover">
              Generate new →
            </Link>
          </CardHeader>
          <CardBody>
            {setups.loading ? (
              <LoadingState />
            ) : setups.error ? (
              <ErrorState message={setups.error} onRetry={setups.refetch} />
            ) : !setups.data || setups.data.items.length === 0 ? (
              <EmptyState
                title="No setups generated yet"
                description="Head to the Analysis page and run an analysis on a symbol to generate the first one."
              />
            ) : (
              <ul className="divide-y divide-border">
                {setups.data.items.map((setup) => (
                  <li key={setup.id} className="flex items-center justify-between gap-4 py-3">
                    <div className="flex items-center gap-3">
                      <DirectionBadge direction={setup.direction} />
                      <div>
                        <p className="text-sm font-medium text-ink-primary">
                          {setup.symbol}{" "}
                          <span className="font-normal text-ink-muted">({setup.timeframe})</span>
                        </p>
                        <p className="text-xs text-ink-muted">{formatDateTime(setup.created_at)}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <Badge tone={setup.status === "PROPOSED" ? "accent" : "neutral"}>
                        {setup.status}
                      </Badge>
                      <div className="w-32">
                        <ConfidenceBar confidence={setup.confidence_score} direction={setup.direction} />
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
