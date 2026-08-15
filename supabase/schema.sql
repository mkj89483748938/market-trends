-- Market Trends dashboard schema.
-- Isolated under its own schema so it doesn't collide with anything else
-- in this Supabase project (e.g. an existing lead-cache table in `public`).
--
-- Run this once in the Supabase SQL Editor (Project -> SQL Editor -> New query).

create schema if not exists market_trends;

create table if not exists market_trends.cities (
  id uuid primary key default gen_random_uuid(),
  slug text unique not null,
  name text not null,
  county text not null default 'Orange County',
  state text not null default 'CA',
  latitude numeric,
  longitude numeric,
  created_at timestamptz not null default now()
);

create table if not exists market_trends.market_stats (
  id uuid primary key default gen_random_uuid(),
  city_id uuid not null references market_trends.cities(id) on delete cascade,
  run_date date not null,

  active_inventory integer,
  new_listings_7d integer,
  new_listings_30d integer,
  pending_count integer,
  months_of_supply numeric,
  median_list_price numeric,
  avg_list_price numeric,
  median_price_per_sqft numeric,
  median_dom numeric,

  homes_sold_30d integer,
  median_sold_price numeric,
  sold_to_list_ratio numeric,

  price_change_mom numeric,
  price_change_yoy numeric,
  inventory_change_mom numeric,
  inventory_change_yoy numeric,
  homes_sold_change_yoy numeric,
  dom_change_yoy numeric,

  created_at timestamptz not null default now(),
  unique (city_id, run_date)
);

create table if not exists market_trends.talking_points (
  id uuid primary key default gen_random_uuid(),
  city_id uuid not null references market_trends.cities(id) on delete cascade,
  run_date date not null,
  audience text not null check (audience in ('buyer', 'seller')),
  points jsonb not null,
  created_at timestamptz not null default now(),
  unique (city_id, run_date, audience)
);

create table if not exists market_trends.active_listings (
  id uuid primary key default gen_random_uuid(),
  city_id uuid not null references market_trends.cities(id) on delete cascade,
  run_date date not null,
  address text,
  list_price numeric,
  beds numeric,
  baths numeric,
  sqft numeric,
  days_on_market integer,
  property_url text,
  created_at timestamptz not null default now()
);

create index if not exists market_stats_city_date_idx
  on market_trends.market_stats (city_id, run_date desc);

create index if not exists active_listings_city_date_idx
  on market_trends.active_listings (city_id, run_date desc);

-- Convenience views: latest row per city (and per city+audience for talking points).
create or replace view market_trends.latest_market_stats as
select distinct on (city_id) *
from market_trends.market_stats
order by city_id, run_date desc;

create or replace view market_trends.latest_talking_points as
select distinct on (city_id, audience) *
from market_trends.talking_points
order by city_id, audience, run_date desc;

create or replace view market_trends.latest_active_listings as
select al.*
from market_trends.active_listings al
join (
  select city_id, max(run_date) as run_date
  from market_trends.active_listings
  group by city_id
) latest on latest.city_id = al.city_id and latest.run_date = al.run_date;

-- RLS with no policies = default-deny for anon/authenticated clients.
-- The app and scraper both use the service role key, which bypasses RLS,
-- so this has no effect on how the dashboard works — it just means these
-- tables stay locked down if `market_trends` is ever exposed via the API.
alter table market_trends.cities enable row level security;
alter table market_trends.market_stats enable row level security;
alter table market_trends.talking_points enable row level security;
alter table market_trends.active_listings enable row level security;

-- Creating a schema does not by itself grant Supabase's Postgres roles
-- access to it. The app and scraper only ever use the service role key
-- (which already bypasses RLS above), so it's the only role granted here —
-- anon/authenticated stay locked out, matching the RLS policy above.
grant usage on schema market_trends to service_role;
grant all privileges on all tables in schema market_trends to service_role;
grant all privileges on all sequences in schema market_trends to service_role;

alter default privileges in schema market_trends
  grant all privileges on tables to service_role;
alter default privileges in schema market_trends
  grant all privileges on sequences to service_role;

-- Additive migration: new metrics (months of supply, pending listings, new
-- listings this week, a corrected homes-sold-change field). Safe to re-run;
-- only needed once against an existing deployment created before this was
-- added to the CREATE TABLE above.
alter table market_trends.market_stats add column if not exists new_listings_7d integer;
alter table market_trends.market_stats add column if not exists pending_count integer;
alter table market_trends.market_stats add column if not exists months_of_supply numeric;
alter table market_trends.market_stats add column if not exists homes_sold_change_yoy numeric;
