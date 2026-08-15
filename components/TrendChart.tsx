"use client";

import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { MarketStats } from "@/lib/types";

type NumericStatsKey = {
  [K in keyof MarketStats]: MarketStats[K] extends number | null ? K : never;
}[keyof MarketStats];

// `kind` (rather than formatter functions) so all props stay serializable
// across the server -> client boundary — this is a client component
// instantiated from an async server component page.
type TrendChartKind = "currency" | "count";

export function TrendChart({
  history,
  field,
  title,
  tooltipLabel,
  color = "#2f6fed",
  kind,
  unit,
  emptyMessage,
}: {
  history: MarketStats[];
  field: NumericStatsKey;
  title: string;
  tooltipLabel: string;
  color?: string;
  kind: TrendChartKind;
  unit?: string;
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

  const formatTick = (value: number) =>
    kind === "currency" ? `$${Math.round(value / 1000)}k` : `${value}`;
  const formatValue = (value: number) =>
    kind === "currency" ? `$${value.toLocaleString()}` : `${value}${unit ? ` ${unit}` : ""}`;

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
