export type City = {
  id: string;
  slug: string;
  name: string;
  county: string;
  state: string;
  latitude: number | null;
  longitude: number | null;
};

export type MarketStats = {
  id: string;
  city_id: string;
  run_date: string;
  active_inventory: number | null;
  new_listings_30d: number | null;
  median_list_price: number | null;
  avg_list_price: number | null;
  median_price_per_sqft: number | null;
  median_dom: number | null;
  homes_sold_30d: number | null;
  median_sold_price: number | null;
  sold_to_list_ratio: number | null;
  price_change_mom: number | null;
  price_change_yoy: number | null;
  inventory_change_mom: number | null;
  inventory_change_yoy: number | null;
  dom_change_yoy: number | null;
};

export type Audience = "buyer" | "seller";

export type TalkingPoints = {
  id: string;
  city_id: string;
  run_date: string;
  audience: Audience;
  points: string[];
};

export type ActiveListing = {
  id: string;
  city_id: string;
  run_date: string;
  address: string | null;
  list_price: number | null;
  beds: number | null;
  baths: number | null;
  sqft: number | null;
  days_on_market: number | null;
  property_url: string | null;
};
