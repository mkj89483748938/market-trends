import { trendDirection } from "@/lib/format";

export function StatTile({
  label,
  value,
  change,
}: {
  label: string;
  value: string;
  change?: number | null;
}) {
  const direction = trendDirection(change);
  const changeColor =
    direction === "up"
      ? "text-emerald-600 dark:text-emerald-400"
      : direction === "down"
        ? "text-red-600 dark:text-red-400"
        : "text-slate-400 dark:text-slate-500";
  const arrow = direction === "up" ? "↑" : direction === "down" ? "↓" : "→";
  const trendText = direction === "up" ? "Trending up" : direction === "down" ? "Declining" : "Flat";

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-800">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-slate-900 dark:text-slate-100">{value}</p>
      {change != null && (
        <p className={`mt-1 text-xs font-medium ${changeColor}`}>
          {arrow} {trendText}
        </p>
      )}
    </div>
  );
}
