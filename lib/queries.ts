import "server-only";
import { getServiceClient } from "./supabase";
import type { ActiveListing, Audience, City, MarketStats, TalkingPoints } from "./types";

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

export async function getLatestStatsByCity(): Promise<Map<string, MarketStats>> {
  const supabase = getServiceClient();
  const { data, error } = await supabase.from("latest_market_stats").select("*");
  if (error) throw error;
  const map = new Map<string, MarketStats>();
  for (const row of data ?? []) map.set(row.city_id, row as MarketStats);
  return map;
}

export async function getLatestStatsForCity(cityId: string): Promise<MarketStats | null> {
  const supabase = getServiceClient();
  const { data, error } = await supabase
    .from("latest_market_stats")
    .select("*")
    .eq("city_id", cityId)
    .maybeSingle();
  if (error) throw error;
  return data;
}

export async function getStatsHistory(cityId: string, limit = 26): Promise<MarketStats[]> {
  const supabase = getServiceClient();
  const { data, error } = await supabase
    .from("market_stats")
    .select("*")
    .eq("city_id", cityId)
    .order("run_date", { ascending: true })
    .limit(limit);
  if (error) throw error;
  return data ?? [];
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

export async function getLatestActiveListings(cityId: string, limit = 12): Promise<ActiveListing[]> {
  const supabase = getServiceClient();
  const { data, error } = await supabase
    .from("latest_active_listings")
    .select("*")
    .eq("city_id", cityId)
    .order("list_price", { ascending: false })
    .limit(limit);
  if (error) throw error;
  return data ?? [];
}
