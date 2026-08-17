"use client";

import { useEffect, useState } from "react";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { formatShortDate } from "@/lib/format";
import type { MarketStats } from "@/lib/types";

type NumericStatsKey = {
  [K in keyof MarketStats]: MarketStats[K] extends number | null ? K : never;
}[keyof MarketStats];

// `kind` (rather than formatter functions) so all props stay serializable
// across the server -> client boundary — this is a client component
// instantiated from an async server component page.
type TrendChartKind = "currency" | "count";

// Recharts colors are plain SVG attributes/inline styles, not Tailwind
// classes, so they don't pick up `dark:` variants automatically — this
// watches the `dark` class on <html> (toggled by ThemeToggle, which can
// change at any time without a page reload) and swaps the palette used for
// the parts of the chart Tailwind can't reach.
function useIsDark() {
  const [isDark, setIsDark] = useState(false);
  useEffect(() => {
    const root = document.documentElement;
    const update = () => setIsDark(root.classList.contains("dark"));
    update();
    const observer = new MutationObserver(update);
    observer.observe(root, { attributes: true, attributeFilter: ["class"] });
    return () => observer.disconnect();
  }, []);
  return isDark;
}

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
  const isDark = useIsDark();

  const points = history
    .map((row) => ({ date: row.run_date, value: row[field] as number | null }))
    .filter((row): row is { date: string; value: number } => row.value != null);

  if (points.length < 2) {
    return (
      <div className="flex h-64 items-center justify-center rounded-xl border border-slate-200 bg-white text-sm text-slate-400 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-500">
        {emptyMessage}
      </div>
    );
  }

  const data = points.map((row) => ({
    date: formatShortDate(row.date),
    value: row.value,
  }));

  const formatTick = (value: number) =>
    kind === "currency" ? `$${Math.round(value / 1000)}k` : `${value}`;
  const formatValue = (value: number) =>
    kind === "currency" ? `$${value.toLocaleString()}` : `${value}${unit ? ` ${unit}` : ""}`;

  const axisColor = isDark ? "#64748b" : "#94a3b8";
  const tooltipStyle = isDark
    ? { backgroundColor: "#1e293b", border: "1px solid #334155", color: "#e2e8f0" }
    : { backgroundColor: "#ffffff", border: "1px solid #e2e8f0", color: "#0f172a" };

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-800">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">{title}</p>
      <div className="mt-2 h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
            <XAxis dataKey="date" tick={{ fontSize: 12, fill: axisColor }} stroke={axisColor} />
            <YAxis
              tick={{ fontSize: 12, fill: axisColor }}
              stroke={axisColor}
              width={70}
              tickFormatter={formatTick}
            />
            <Tooltip
              formatter={(value: number) => [formatValue(value), tooltipLabel]}
              contentStyle={tooltipStyle}
              labelStyle={{ color: tooltipStyle.color }}
            />
            <Line type="monotone" dataKey="value" stroke={color} strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
