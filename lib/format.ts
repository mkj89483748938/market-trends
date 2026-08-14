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

export function trendDirection(value: number | null | undefined): "up" | "down" | "flat" {
  if (value == null || Math.abs(value) < 0.05) return "flat";
  return value > 0 ? "up" : "down";
}
