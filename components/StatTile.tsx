import { trendDirection } from "@/lib/format";

export function StatTile({
  label,
  value,
  change,
  changeLabel = "YoY",
}: {
  label: string;
  value: string;
  change?: number | null;
  changeLabel?: string;
}) {
  const direction = trendDirection(change);
  const changeColor =
    direction === "up" ? "text-emerald-600" : direction === "down" ? "text-red-600" : "text-slate-400";
  const arrow = direction === "up" ? "↑" : direction === "down" ? "↓" : "→";

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-slate-900">{value}</p>
      {change != null && (
        <p className={`mt-1 text-xs font-medium ${changeColor}`}>
          {arrow} {Math.abs(change).toFixed(1)}% {changeLabel}
        </p>
      )}
    </div>
  );
}
