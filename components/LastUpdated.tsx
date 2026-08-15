import { daysSince, formatRelativeDays, formatRunDate } from "@/lib/format";

// The scraper runs weekly (Mondays). Anything older than ~10 days means a
// run was missed or failed, which is worth flagging rather than quietly
// showing week-old figures as if they were current.
const STALE_AFTER_DAYS = 10;

export function LastUpdated({ runDate }: { runDate: string | null }) {
  if (!runDate) {
    return (
      <p className="text-xs text-slate-500 dark:text-slate-400">
        No market data loaded yet — the first scrape hasn&apos;t completed.
      </p>
    );
  }

  const age = daysSince(runDate);
  const isStale = age != null && age > STALE_AFTER_DAYS;

  return (
    <div
      className={`inline-flex flex-wrap items-center gap-x-2 gap-y-1 rounded-lg border px-3 py-1.5 text-xs ${
        isStale
          ? "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-300"
          : "border-slate-200 bg-white text-slate-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-400"
      }`}
    >
      <span>
        <span className="font-medium">Data last updated:</span> {formatRunDate(runDate)}
        {age != null && <span className="text-slate-400 dark:text-slate-500"> ({formatRelativeDays(age)})</span>}
      </span>
      <span className={isStale ? "" : "text-slate-400 dark:text-slate-500"}>
        {isStale
          ? "· A weekly refresh looks like it was missed — figures below may be out of date."
          : "· Refreshes automatically every Monday from Realtor.com."}
      </span>
    </div>
  );
}
