# OC Market Trends

A real estate market trends dashboard for agents, covering all 34 incorporated
cities in Orange County, CA. Each city page shows current stats, trend charts,
and LLM-generated talking points agents can use with buyers or sellers.

## How it works

- **`scraper/`** (Python) — pulls listing data from Realtor.com via
  [HomeHarvest](https://github.com/ZacharyHampton/HomeHarvest), aggregates it
  into per-city stats, generates buyer/seller talking points with the
  Anthropic API, and writes everything to Supabase. Runs on a schedule via
  GitHub Actions (`.github/workflows/scrape.yml`, weekly by default).
- **Next.js app** (`app/`, `components/`, `lib/`) — reads from Supabase and
  renders the dashboard. Deployed on Vercel. All Supabase access happens
  server-side with the service role key — nothing is exposed to the browser.
- **Auth** — none. The dashboard is publicly readable: it only shows
  aggregate market data, and page views cost nothing (talking points are
  generated during the weekly scrape, not per request). Supabase is still
  only ever reached server-side with the service role key, so no credential
  and no write path is exposed to the browser.

Data lives in its own `market_trends` Postgres schema, so it can share a
Supabase project with other apps (e.g. a lead-cache table in `public`)
without colliding.

## One-time setup

### 1. Supabase

1. Open your Supabase project → SQL Editor → New query.
2. Paste in the contents of `supabase/schema.sql` and run it. This creates
   the `market_trends` schema and its tables/views — it does not touch
   anything in `public` or elsewhere. The whole file is safe to re-run any
   time (e.g. after pulling an update that adds new columns) — everything
   is `if not exists` / additive.
3. Go to Project Settings → Data API, and add `market_trends` to the
   **Exposed schemas** field (it defaults to `public, graphql_public` — the
   REST API returns `PGRST106: Invalid schema` for any table outside that
   list). Save; the change applies within a few seconds.

### 2. Vercel (Next.js app)

Connect this repo in Vercel, then set these environment variables in
**Project Settings → Environment Variables**:

| Variable | Value |
|---|---|
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Your Supabase service role key (server-only — never prefix with `NEXT_PUBLIC_`) |

### 3. GitHub Actions (scraper)

In this repo's **Settings → Secrets and variables → Actions**, add:

| Secret | Value |
|---|---|
| `SUPABASE_URL` | Same Supabase project URL as above |
| `SUPABASE_SERVICE_ROLE_KEY` | Same service role key as above |
| `ANTHROPIC_API_KEY` | An Anthropic API key from console.anthropic.com (separate, metered billing — not a claude.ai subscription) |

Once secrets are set, trigger the workflow manually the first time from the
**Actions** tab (`Scrape OC market data` → `Run workflow`) instead of waiting
for the weekly schedule, so the dashboard has data right away.

### 4. Backfill sold-price history (optional, one-time)

The weekly scraper only knows about *active* inventory and list price as a
live snapshot — there's no way to ask Realtor.com what was active a year
ago. Sold-price history is different: it can be queried for any past date
range, so run the **"Backfill sold-price history"** workflow once (Actions
tab → `workflow_dispatch`, default 6 months) to seed the median-sold-price
trend chart with real history immediately, instead of waiting months for
weekly runs to build it up. The active-inventory trend chart can't be
backfilled the same way — it fills in naturally as weekly runs accumulate.

## Local development

```bash
npm install
cp .env.example .env.local   # fill in SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
npm run dev
```

To run the scraper locally:

```bash
cd scraper
pip install -r requirements.txt
export SUPABASE_URL=...
export SUPABASE_SERVICE_ROLE_KEY=...
export ANTHROPIC_API_KEY=...
python main.py
```

## Property-type segments

Each run writes three rows per city — `all`, `single_family`, and
`condo_townhome` — and the city page has a matching toggle (All types /
Houses / Condos & Townhomes). Segmenting happens locally, in pandas, off the
`style` field of the listings already fetched, so it costs no extra requests
to Realtor.com.

This exists because a blended all-types number doesn't reconcile against the
Altos-powered reports agents already see (BHHS "Your Local Market Report"),
which split Houses / Condos / Co-Op. Irvine was the clearest example: our
all-types view showed ~3x the inventory and a ~35% lower median list price
than the Altos Houses tab, purely from mixing condos into the same number.

Listings whose type is neither (land, mobile, multi-family, farm) count
toward `all` only — the same way Altos leaves land out of its Houses tab.

## Reconciling against Altos / other market reports

Expect our figures to be *close to* but not identical to Altos, even
segment-for-segment. Known reasons, in rough order of impact:

1. **Property type** — the big one, addressed by the segment toggle above.
   Compare like for like: our "Houses" against their "Houses" tab.
2. **Geography** — Altos defines its own market areas (often zip-based);
   HomeHarvest resolves Realtor.com's city boundary. Unincorporated pockets
   near a city can land on either side of the line.
3. **Days on market** — Realtor.com's `days_on_mls` generally resets when a
   listing is relisted, biasing our DOM lower. Altos reports a separate
   "relisted %" precisely because this is significant.
4. **Source tier** — Altos ingests MLS feeds under license; we read
   Realtor.com's public listing data, which is MLS-derived but filtered and
   slightly delayed.

Treat this dashboard as a fast directional read, not a system of record. For
anything going in front of a client as a precise figure, reconcile against
the MLS.

## Notes / known limitations (v1)

- The city page's bottom table shows **recently closed sales**, not active
  listings. Sold prices are what homes actually traded for; asking prices
  are a softer claim to put in front of a client. Active listings are still
  scraped and stored (`active_listings`), just not displayed — the
  inventory/DOM/list-price tiles above are all computed from them.
- Every page shows a **"Data last updated"** note with the date of the run
  that produced the figures on screen. It turns amber past 10 days, which
  means a weekly run was missed or failed — the dashboard has no way to tell
  the difference between "the market didn't move" and "the scraper didn't
  run", so it says which data it's showing instead of guessing.
- Talking points are deliberately **whole-market** (all property types) and
  are not segmented, so the same bullets show on every tab of the segment
  toggle. They avoid percentages by design — movement is described in words
  ("prices are higher than three months ago") rather than in figures an agent
  would then have to defend to a client.
- Talking points are generated **once per scrape run**, not per page view:
  one API call per city per week, written to the `talking_points` table, and
  the dashboard only ever reads stored rows. Agents refreshing a city page
  all day costs nothing.
- **Active inventory excludes homes already under contract.** Realtor.com's
  for-sale feed carries some listings that are in escrow, which would inflate
  both inventory and months of supply; the scraper drops anything the feed
  flags as pending/under contract and anything that also appears in the
  dedicated pending query. Contingent listings are kept — they're still
  taking backup offers.
- Two trend charts, two different data sources: **median sold price** comes
  from date-ranged sold-listing queries, so it can be backfilled (see step 4
  above) and has real history from day one. **Active inventory** is only
  ever a live snapshot, so that chart — along with `inventory_change_mom`/
  `inventory_change_yoy` on the stat tiles — has no way to backfill and
  instead builds up from our own accumulated weekly runs, comparing each
  run against the nearest prior run ~30/~365 days back once enough exist.
  Price and homes-sold month-over-month/year-over-year percentages don't
  have this limitation — they're computed fresh each run from Realtor.com's
  own historical sold data.
- HomeHarvest scrapes Realtor.com; it's not an official API, so treat the
  weekly cadence as the default and avoid tightening it to daily without a
  reason — a scraping failure for one city is logged and skipped rather than
  failing the whole run.
- Talking points are generated by Claude from that run's stats. They're
  meant as a starting point for a conversation, not vetted legal/financial
  advice — worth a skim before an agent uses them verbatim.
