import "server-only";
import { getServiceClient } from "./supabase";
import type {
  ActiveListing,
  Audience,
  City,
  MarketStats,
  PropertySegment,
  TalkingPoints,
} from "./types";

export async function getCities(): Promise<City[]> {
  const supabase = getServiceClient();
  const { data, error } = await supabase.from("cities").select("*").order("name");
  if (error) throw error;
  return data ?? [];
}

export async function getCityBySlug(slug: string): Promise<City | null> {
  const supabase = getServiceClient();
  const { data, error } = await supabase
    .from("cities")
    .select("*")
    .eq("slug", slug)
    .maybeSingle();
  if (error) throw error;
  return data;
}

export async function getLatestStatsByCity(
  segment: PropertySegment = "all"
): Promise<Map<string, MarketStats>> {
  const supabase = getServiceClient();
  const { data, error } = await supabase
    .from("latest_market_stats")
    .select("*")
    .eq("property_segment", segment);
  if (error) throw error;
  const map = new Map<string, MarketStats>();
  for (const row of data ?? []) map.set(row.city_id, row as MarketStats);
  return map;
}

/**
 * Most recent run_date across every city — i.e. when the data last refreshed.
 * Reads market_stats rather than latest_market_stats so it reflects the newest
 * run even if a city or two failed to write that week.
 */
export async function getLastUpdated(): Promise<string | null> {
  const supabase = getServiceClient();
  const { data, error } = await supabase
    .from("market_stats")
    .select("run_date")
    .order("run_date", { ascending: false })
    .limit(1)
    .maybeSingle();
  if (error) throw error;
  return data?.run_date ?? null;
}

export async function getLatestStatsForCity(
  cityId: string,
  segment: PropertySegment = "all"
): Promise<MarketStats | null> {
  const supabase = getServiceClient();
  const { data, error } = await supabase
    .from("latest_market_stats")
    .select("*")
    .eq("city_id", cityId)
    .eq("property_segment", segment)
    .maybeSingle();
  if (error) throw error;
  return data;
}

export async function getStatsHistory(
  cityId: string,
  segment: PropertySegment = "all",
  limit = 60
): Promise<MarketStats[]> {
  const supabase = getServiceClient();
  // Order descending + limit to get the most recent rows, then reverse to
  // chronological order for the chart. Ordering ascending-then-limit (the
  // original approach) grabs the OLDEST rows instead once a city has more
  // than `limit` rows on record, silently freezing the trend chart on old
  // data instead of showing the latest weeks.
  const { data, error } = await supabase
    .from("market_stats")
    .select("*")
    .eq("city_id", cityId)
    .eq("property_segment", segment)
    .order("run_date", { ascending: false })
    .limit(limit);
  if (error) throw error;
  return (data ?? []).reverse();
}

export async function getLatestTalkingPoints(cityId: string): Promise<Record<Audience, string[]>> {
  const supabase = getServiceClient();
  const { data, error } = await supabase
    .from("latest_talking_points")
    .select("*")
    .eq("city_id", cityId);
  if (error) throw error;

  const result: Record<Audience, string[]> = { buyer: [], seller: [] };
  for (const row of (data ?? []) as TalkingPoints[]) {
    result[row.audience] = row.points ?? [];
  }
  return result;
}

export async function getLatestActiveListings(
  cityId: string,
  segment: PropertySegment = "all",
  limit = 12
): Promise<ActiveListing[]> {
  const supabase = getServiceClient();
  // Sorted by days-on-market ascending (lowest first) as a proxy for recency
  // — this table is labeled "Recent active listings" in the UI, but was
  // previously sorted by price descending, which isn't the same thing.
  const { data, error } = await supabase
    .from("latest_active_listings")
    .select("*")
    .eq("city_id", cityId)
    .eq("property_segment", segment)
    .order("days_on_market", { ascending: true, nullsFirst: false })
    .limit(limit);
  if (error) throw error;
  return data ?? [];
}
