import { CityCard } from "@/components/CityCard";
import { getCities, getLatestStatsByCity } from "@/lib/queries";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const [cities, statsByCity] = await Promise.all([getCities(), getLatestStatsByCity()]);

  return (
    <main className="mx-auto max-w-6xl px-4 py-10">
      <header className="mb-8">
        <h1 className="text-2xl font-semibold text-slate-900">OC Market Trends</h1>
        <p className="mt-1 text-sm text-slate-500">
          Orange County city-by-city market stats, trends, and client talking points.
        </p>
      </header>

      {cities.length === 0 ? (
        <p className="text-sm text-slate-500">
          No cities loaded yet. Run the schema migration and the scraper to populate data.
        </p>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {cities.map((city) => (
            <CityCard key={city.id} city={city} stats={statsByCity.get(city.id)} />
          ))}
        </div>
      )}
    </main>
  );
}
