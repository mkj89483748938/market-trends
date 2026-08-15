import { notFound } from "next/navigation";
import Link from "next/link";
import { StatTile } from "@/components/StatTile";
import { TrendChart } from "@/components/TrendChart";
import { TalkingPoints } from "@/components/TalkingPoints";
import { formatCurrency, formatDays, formatNumber, formatPercent } from "@/lib/format";
import {
  getCityBySlug,
  getLatestActiveListings,
  getLatestStatsForCity,
  getLatestTalkingPoints,
  getStatsHistory,
} from "@/lib/queries";

export const dynamic = "force-dynamic";

export default async function CityPage({ params }: { params: { slug: string } }) {
  const city = await getCityBySlug(params.slug);
  if (!city) notFound();

  const [stats, history, talkingPoints, listings] = await Promise.all([
    getLatestStatsForCity(city.id),
    getStatsHistory(city.id),
    getLatestTalkingPoints(city.id),
    getLatestActiveListings(city.id),
  ]);

  return (
    <main className="mx-auto max-w-6xl px-4 py-10">
      <Link href="/" className="text-sm text-brand-600 hover:underline">
        ← All cities
      </Link>

      <header className="mt-2 mb-8">
        <h1 className="text-2xl font-semibold text-slate-900">{city.name}</h1>
        <p className="mt-1 text-sm text-slate-500">
          {stats ? `Updated ${new Date(stats.run_date).toLocaleDateString()}` : "No data yet"}
        </p>
      </header>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
        <StatTile label="Median sold price" value={formatCurrency(stats?.median_sold_price)} change={stats?.price_change_yoy} />
        <StatTile label="Median list price" value={formatCurrency(stats?.median_list_price)} />
        <StatTile label="$ / sqft" value={formatCurrency(stats?.median_price_per_sqft)} />
        <StatTile label="Median days on market" value={formatDays(stats?.median_dom)} change={stats?.dom_change_yoy} />
        <StatTile label="Active inventory" value={formatNumber(stats?.active_inventory)} change={stats?.inventory_change_yoy} />
        <StatTile label="Months of supply" value={stats?.months_of_supply != null ? `${stats.months_of_supply.toFixed(1)} mo` : "—"} />
        <StatTile label="New listings (7d)" value={formatNumber(stats?.new_listings_7d)} />
        <StatTile label="Pending" value={formatNumber(stats?.pending_count)} />
        <StatTile label="Homes sold (30d)" value={formatNumber(stats?.homes_sold_30d)} change={stats?.homes_sold_change_yoy} />
        <StatTile label="Sold-to-list ratio" value={stats?.sold_to_list_ratio != null ? `${stats.sold_to_list_ratio.toFixed(1)}%` : "—"} />
        <StatTile label="Price change (MoM)" value={formatPercent(stats?.price_change_mom)} />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <TrendChart
          history={history}
          field="median_sold_price"
          title="Median sold price over time"
          tooltipLabel="Median sold price"
          formatTick={(v) => `$${Math.round(v / 1000)}k`}
          formatValue={(v) => `$${v.toLocaleString()}`}
          emptyMessage="Sold-price history will appear once the backfill or a few weekly runs have completed."
        />
        <TrendChart
          history={history}
          field="active_inventory"
          title="Active inventory over time"
          tooltipLabel="Active inventory"
          color="#16a34a"
          formatTick={(v) => `${v}`}
          formatValue={(v) => `${v} homes`}
          emptyMessage="Inventory trend builds up week by week — check back after a few scrape runs."
        />
      </div>

      <div className="mt-6">
        <TalkingPoints points={talkingPoints} />
      </div>

      {listings.length > 0 && (
        <div className="mt-6 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
            Recent active listings
          </p>
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="text-slate-500">
                  <th className="pb-2 pr-4 font-medium">Address</th>
                  <th className="pb-2 pr-4 font-medium">Price</th>
                  <th className="pb-2 pr-4 font-medium">Beds/Baths</th>
                  <th className="pb-2 pr-4 font-medium">Sqft</th>
                  <th className="pb-2 font-medium">DOM</th>
                </tr>
              </thead>
              <tbody>
                {listings.map((listing) => (
                  <tr key={listing.id} className="border-t border-slate-100">
                    <td className="py-2 pr-4">
                      {listing.property_url ? (
                        <a
                          href={listing.property_url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-brand-600 hover:underline"
                        >
                          {listing.address ?? "View listing"}
                        </a>
                      ) : (
                        (listing.address ?? "—")
                      )}
                    </td>
                    <td className="py-2 pr-4">{formatCurrency(listing.list_price)}</td>
                    <td className="py-2 pr-4">
                      {listing.beds ?? "—"} / {listing.baths ?? "—"}
                    </td>
                    <td className="py-2 pr-4">{formatNumber(listing.sqft)}</td>
                    <td className="py-2">{listing.days_on_market ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </main>
  );
}
