import Link from "next/link";
import { formatCurrency, formatDays, formatNumber, trendDirection } from "@/lib/format";
import type { City, MarketStats } from "@/lib/types";

export function CityCard({ city, stats }: { city: City; stats?: MarketStats }) {
  const direction = trendDirection(stats?.price_change_yoy);
  const badgeColor =
    direction === "up"
      ? "bg-emerald-50 text-emerald-700"
      : direction === "down"
        ? "bg-red-50 text-red-700"
        : "bg-slate-100 text-slate-600";

  return (
    <Link
      href={`/city/${city.slug}`}
      className="block rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-brand-500 hover:shadow-md"
    >
      <div className="flex items-start justify-between">
        <h3 className="font-semibold text-slate-900">{city.name}</h3>
        {stats?.price_change_yoy != null && (
          <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${badgeColor}`}>
            {direction === "up" ? "↑ Trending up" : direction === "down" ? "↓ Declining" : "→ Flat"}
          </span>
        )}
      </div>

      {stats ? (
        <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
          <div>
            <dt className="text-slate-500">Median price</dt>
            <dd className="font-medium text-slate-900">{formatCurrency(stats.median_list_price)}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Inventory</dt>
            <dd className="font-medium text-slate-900">{formatNumber(stats.active_inventory)}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Median DOM</dt>
            <dd className="font-medium text-slate-900">{formatDays(stats.median_dom)}</dd>
          </div>
          <div>
            <dt className="text-slate-500">$ / sqft</dt>
            <dd className="font-medium text-slate-900">{formatCurrency(stats.median_price_per_sqft)}</dd>
          </div>
        </dl>
      ) : (
        <p className="mt-4 text-sm text-slate-400">No data yet — waiting on first scrape run.</p>
      )}
    </Link>
  );
}
