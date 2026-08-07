import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import type { WinRateReport } from "@/types";

interface WinLossPieProps {
  report: WinRateReport;
  size?: number;
}

export function WinLossPie({ report, size = 160 }: WinLossPieProps) {
  const data = [
    { name: "Wins", value: report.wins, color: "rgb(var(--color-bull))" },
    { name: "Losses", value: report.losses, color: "rgb(var(--color-bear))" },
    { name: "Breakeven", value: report.breakevens, color: "rgb(var(--color-ink-muted))" },
  ].filter((d) => d.value > 0);

  if (data.length === 0) {
    return (
      <div
        style={{ width: size, height: size }}
        className="flex items-center justify-center rounded-full border border-dashed border-border text-xs text-ink-muted"
      >
        No trades yet
      </div>
    );
  }

  return (
    <ResponsiveContainer width={size} height={size}>
      <PieChart>
        <Pie
          data={data}
          dataKey="value"
          nameKey="name"
          innerRadius={size / 2 - 28}
          outerRadius={size / 2 - 8}
          paddingAngle={data.length > 1 ? 3 : 0}
          strokeWidth={0}
        >
          {data.map((entry) => (
            <Cell key={entry.name} fill={entry.color} />
          ))}
        </Pie>
        <Tooltip
          contentStyle={{
            background: "rgb(var(--color-surface-raised))",
            border: "1px solid rgb(var(--color-gridline))",
            borderRadius: 8,
            fontSize: 12,
          }}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}
