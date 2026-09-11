import Link from "next/link";
import { formatCurrency, formatDays, formatMonths, formatNumber } from "@/lib/format";
import type { City, MarketStats } from "@/lib/types";

/**
 * County-wide entry point, shown above the city grid. Deliberately styled as
 * a wide banner rather than a 35th card so it doesn't read as just another
 * city — it's the whole county, and the numbers behind it are computed from
 * every city's listings pooled together.
 */
export function CountyCard({ city, stats }: { city: City | null; stats?: MarketStats }) {
  if (!city) return null;

  return (
    <Link
      href={`/city/${city.slug}`}
      className="mb-6 block rounded-xl border border-brand-100 bg-brand-50 p-5 shadow-sm transition hover:border-brand-500 hover:shadow-md dark:border-brand-700 dark:bg-slate-800 dark:hover:border-brand-500"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="font-semibold text-slate-900 dark:text-slate-100">
            All of Orange County
          </h2>
          <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
            Every city combined — county-wide stats, trends and talking points
          </p>
        </div>
        <span className="text-sm font-medium text-brand-600 dark:text-brand-500">
          View county &rarr;
        </span>
      </div>

      {stats ? (
        <dl className="mt-4 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
          <div>
            <dt className="text-slate-500 dark:text-slate-400">Median sold price</dt>
            <dd className="font-medium text-slate-900 dark:text-slate-100">
              {formatCurrency(stats.median_sold_price)}
            </dd>
          </div>
          <div>
            <dt className="text-slate-500 dark:text-slate-400">Homes for sale</dt>
            <dd className="font-medium text-slate-900 dark:text-slate-100">
              {formatNumber(stats.active_inventory)}
            </dd>
          </div>
          <div>
            <dt className="text-slate-500 dark:text-slate-400">Median DOM</dt>
            <dd className="font-medium text-slate-900 dark:text-slate-100">
              {formatDays(stats.median_dom)}
            </dd>
          </div>
          <div>
            <dt className="text-slate-500 dark:text-slate-400">Months of supply</dt>
            <dd className="font-medium text-slate-900 dark:text-slate-100">
              {formatMonths(stats.months_of_supply)}
            </dd>
          </div>
        </dl>
      ) : (
        <p className="mt-4 text-sm text-slate-500 dark:text-slate-400">
          County figures appear after the next scrape run completes.
        </p>
      )}
    </Link>
  );
}
