import { format } from "date-fns";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { AccountSnapshot } from "@/types";

interface EquityCurveChartProps {
  snapshots: AccountSnapshot[];
  height?: number;
}

export function EquityCurveChart({ snapshots, height = 260 }: EquityCurveChartProps) {
  const data = snapshots
    .slice()
    .reverse()
    .map((s) => ({
      time: s.created_at,
      equity: s.equity,
      balance: s.balance,
    }));

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
        <defs>
          <linearGradient id="equityFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="rgb(var(--color-accent))" stopOpacity={0.35} />
            <stop offset="100%" stopColor="rgb(var(--color-accent))" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke="rgb(var(--color-gridline))" vertical={false} />
        <XAxis
          dataKey="time"
          tickFormatter={(value: string) => format(new Date(value), "MMM d")}
          stroke="rgb(var(--color-ink-muted))"
          tick={{ fontSize: 11 }}
          axisLine={{ stroke: "rgb(var(--color-gridline))" }}
          tickLine={false}
          minTickGap={40}
        />
        <YAxis
          width={64}
          stroke="rgb(var(--color-ink-muted))"
          tick={{ fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          domain={["auto", "auto"]}
        />
        <Tooltip
          contentStyle={{
            background: "rgb(var(--color-surface-raised))",
            border: "1px solid rgb(var(--color-gridline))",
            borderRadius: 8,
            fontSize: 12,
          }}
          labelFormatter={(value: string) => format(new Date(value), "MMM d, yyyy HH:mm")}
          formatter={(value: number) => value.toFixed(2)}
        />
        <Area
          type="monotone"
          dataKey="equity"
          stroke="rgb(var(--color-accent))"
          strokeWidth={2}
          fill="url(#equityFill)"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
