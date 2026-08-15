export function formatCurrency(value: number | null | undefined): string {
  if (value == null) return "—";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

export function formatNumber(value: number | null | undefined): string {
  if (value == null) return "—";
  return new Intl.NumberFormat("en-US").format(Math.round(value));
}

export function formatPercent(value: number | null | undefined): string {
  if (value == null) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(1)}%`;
}

export function formatDays(value: number | null | undefined): string {
  if (value == null) return "—";
  return `${Math.round(value)} days`;
}

/**
 * Parses a `YYYY-MM-DD` run_date as a LOCAL date.
 *
 * `new Date("2026-08-15")` is specified to parse as UTC midnight, which in
 * Pacific time is 5pm on Aug 14 — so the naive version displays every run
 * date one day early. Splitting the parts sidesteps that entirely.
 */
function parseRunDate(value: string): Date | null {
  const [year, month, day] = value.split("-").map(Number);
  if (!year || !month || !day) return null;
  return new Date(year, month - 1, day);
}

export function formatRunDate(value: string | null | undefined): string {
  if (!value) return "—";
  const parsed = parseRunDate(value);
  if (!parsed) return value;
  return parsed.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

/** Whole days between a run_date and today, or null if unparseable. */
export function daysSince(value: string | null | undefined): number | null {
  if (!value) return null;
  const parsed = parseRunDate(value);
  if (!parsed) return null;
  const today = new Date();
  const startOfToday = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  return Math.round((startOfToday.getTime() - parsed.getTime()) / 86_400_000);
}

export function formatRelativeDays(days: number | null): string {
  if (days == null) return "";
  if (days <= 0) return "today";
  if (days === 1) return "yesterday";
  return `${days} days ago`;
}

export function trendDirection(value: number | null | undefined): "up" | "down" | "flat" {
  if (value == null || Math.abs(value) < 0.05) return "flat";
  return value > 0 ? "up" : "down";
}
