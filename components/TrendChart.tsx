"use client";

import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { MarketStats } from "@/lib/types";

export function TrendChart({ history }: { history: MarketStats[] }) {
  if (history.length < 2) {
    return (
      <div className="flex h-64 items-center justify-center rounded-xl border border-slate-200 bg-white text-sm text-slate-400">
        Trend chart will appear once a few weeks of data have been collected.
      </div>
    );
  }

  const data = history.map((row) => ({
    date: new Date(row.run_date).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
    medianPrice: row.median_list_price,
    inventory: row.active_inventory,
  }));

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
        Median list price over time
      </p>
      <div className="mt-2 h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
            <XAxis dataKey="date" tick={{ fontSize: 12 }} stroke="#94a3b8" />
            <YAxis
              tick={{ fontSize: 12 }}
              stroke="#94a3b8"
              width={70}
              tickFormatter={(v) => `$${Math.round(v / 1000)}k`}
            />
            <Tooltip
              formatter={(value: number) => [`$${value.toLocaleString()}`, "Median list price"]}
            />
            <Line type="monotone" dataKey="medianPrice" stroke="#2f6fed" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
