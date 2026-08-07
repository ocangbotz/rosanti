import { useEffect } from "react";

import { getAccountSnapshots, listAccounts } from "@/api/account";
import { getMonthlyReport, getWeeklyReport } from "@/api/journal";
import { getDrawdown } from "@/api/risk";
import { EquityCurveChart } from "@/components/charts/EquityCurveChart";
import { WinLossPie } from "@/components/charts/WinLossPie";
import { Badge } from "@/components/ui/Badge";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/Spinner";
import { StatTile } from "@/components/ui/StatTile";
import { formatCurrency, formatPercent } from "@/lib/format";
import { useApi } from "@/lib/useApi";
import { useAppStore } from "@/store/useAppStore";

export function PerformancePage() {
  const { accountId, setAccountId } = useAppStore();
  const accounts = useApi(listAccounts, []);

  useEffect(() => {
    if (accountId === null && accounts.data && accounts.data.length > 0) {
      setAccountId(accounts.data[0].id);
    }
  }, [accountId, accounts.data, setAccountId]);

  const snapshots = useApi(() => getAccountSnapshots(accountId!, 200), [accountId], {
    skip: accountId === null,
  });
  const weekly = useApi(() => getWeeklyReport(accountId!), [accountId], { skip: accountId === null });
  const monthly = useApi(() => getMonthlyReport(accountId!), [accountId], { skip: accountId === null });
  const drawdown = useApi(() => getDrawdown(accountId!), [accountId], { skip: accountId === null });

  if (accounts.loading && !accounts.data) return <LoadingState label="Loading accounts…" />;
  if (accounts.error) return <ErrorState message={accounts.error} onRetry={accounts.refetch} />;

  if (!accounts.data || accounts.data.length === 0) {
    return (
      <EmptyState
        title="No broker account configured yet"
        description="Add a broker account in Settings, or let the background scheduler create one automatically once it polls the connected terminal."
      />
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-ink-primary">Performance</h1>
        <p className="text-sm text-ink-muted">Equity curve, win rate, and drawdown for your account.</p>
      </div>

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile
          label="Net P&L (week)"
          value={weekly.data ? formatCurrency(weekly.data.net_profit_loss) : "—"}
          deltaTone={weekly.data && weekly.data.net_profit_loss >= 0 ? "good" : "bad"}
        />
        <StatTile
          label="Net P&L (month)"
          value={monthly.data ? formatCurrency(monthly.data.net_profit_loss) : "—"}
          deltaTone={monthly.data && monthly.data.net_profit_loss >= 0 ? "good" : "bad"}
        />
        <StatTile
          label="Current Drawdown"
          value={drawdown.data ? formatPercent(drawdown.data.current_drawdown_percent) : "—"}
          delta={drawdown.data?.limit_breached ? <Badge tone="critical">Limit breached</Badge> : undefined}
        />
        <StatTile
          label="Max Drawdown Observed"
          value={drawdown.data ? formatPercent(drawdown.data.max_drawdown_observed_percent) : "—"}
        />
      </section>

      <Card>
        <CardHeader>
          <CardTitle>Equity Curve</CardTitle>
        </CardHeader>
        <CardBody>
          {snapshots.loading ? (
            <LoadingState />
          ) : snapshots.error ? (
            <ErrorState message={snapshots.error} onRetry={snapshots.refetch} />
          ) : !snapshots.data || snapshots.data.length === 0 ? (
            <EmptyState title="No equity snapshots yet" description="The scheduler records one on every market poll." />
          ) : (
            <EquityCurveChart snapshots={snapshots.data} />
          )}
        </CardBody>
      </Card>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <ReportCard title="This Week" report={weekly.data} loading={weekly.loading} error={weekly.error} />
        <ReportCard title="This Month" report={monthly.data} loading={monthly.loading} error={monthly.error} />
      </div>
    </div>
  );
}

function ReportCard({
  title,
  report,
  loading,
  error,
}: {
  title: string;
  report: import("@/types").PeriodReport | null;
  loading: boolean;
  error: string | null;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardBody>
        {loading ? (
          <LoadingState />
        ) : error ? (
          <ErrorState message={error} />
        ) : report ? (
          <div className="flex items-center gap-6">
            <WinLossPie report={report.win_rate} />
            <div className="space-y-2 text-sm">
              <p className="text-2xl font-semibold tabular-nums text-ink-primary">
                {formatPercent(report.win_rate.win_rate_percent, 0)}
              </p>
              <p className="text-ink-muted">
                {report.win_rate.wins}W / {report.win_rate.losses}L / {report.win_rate.breakevens}BE
              </p>
              <p>
                Net:{" "}
                <span className={report.net_profit_loss >= 0 ? "text-delta-good" : "text-delta-bad"}>
                  {formatCurrency(report.net_profit_loss)}
                </span>
              </p>
              {report.win_rate.average_r_multiple !== null && (
                <p className="text-ink-muted">Avg R: {report.win_rate.average_r_multiple.toFixed(2)}</p>
              )}
            </div>
          </div>
        ) : null}
      </CardBody>
    </Card>
  );
}
