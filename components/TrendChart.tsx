"use client";

import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { MarketStats } from "@/lib/types";

type NumericStatsKey = {
  [K in keyof MarketStats]: MarketStats[K] extends number | null ? K : never;
}[keyof MarketStats];

export function TrendChart({
  history,
  field,
  title,
  tooltipLabel,
  color = "#2f6fed",
  formatTick,
  formatValue,
  emptyMessage,
}: {
  history: MarketStats[];
  field: NumericStatsKey;
  title: string;
  tooltipLabel: string;
  color?: string;
  formatTick: (value: number) => string;
  formatValue: (value: number) => string;
  emptyMessage: string;
}) {
  const points = history
    .map((row) => ({ date: row.run_date, value: row[field] as number | null }))
    .filter((row): row is { date: string; value: number } => row.value != null);

  if (points.length < 2) {
    return (
      <div className="flex h-64 items-center justify-center rounded-xl border border-slate-200 bg-white text-sm text-slate-400">
        {emptyMessage}
      </div>
    );
  }

  const data = points.map((row) => ({
    date: new Date(row.date).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
    value: row.value,
  }));

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{title}</p>
      <div className="mt-2 h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
            <XAxis dataKey="date" tick={{ fontSize: 12 }} stroke="#94a3b8" />
            <YAxis tick={{ fontSize: 12 }} stroke="#94a3b8" width={70} tickFormatter={formatTick} />
            <Tooltip formatter={(value: number) => [formatValue(value), tooltipLabel]} />
            <Line type="monotone" dataKey="value" stroke={color} strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
