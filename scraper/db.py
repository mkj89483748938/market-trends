import os

from supabase import Client, ClientOptions, create_client

_client: Client | None = None


def get_client() -> Client:
    global _client
    if _client is not None:
        return _client

    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    _client = create_client(url, key, options=ClientOptions(schema="market_trends"))
    return _client


def ensure_cities(cities: list[dict]) -> dict[str, str]:
    """Upserts the OC city list and returns {slug: city_id}."""
    client = get_client()
    client.table("cities").upsert(
        [{"slug": c["slug"], "name": c["name"]} for c in cities],
        on_conflict="slug",
    ).execute()

    rows = client.table("cities").select("id, slug").execute().data
    return {row["slug"]: row["id"] for row in rows}


def upsert_market_stats(row: dict) -> None:
    get_client().table("market_stats").upsert(row, on_conflict="city_id,run_date").execute()


def get_stats_history(city_id: str) -> list[dict]:
    """All prior market_stats rows for a city, oldest first.

    Realtor.com only exposes a live snapshot of active inventory/list price —
    there's no way to query "what was active a year ago". So month-over-month
    and year-over-year changes for those fields are computed by comparing
    against our own accumulated history here, not by re-querying Realtor.com.
    Call this before upserting the current run's row.
    """
    res = (
        get_client()
        .table("market_stats")
        .select("run_date, active_inventory, median_list_price")
        .eq("city_id", city_id)
        .order("run_date")
        .execute()
    )
    return res.data or []


def upsert_talking_points(row: dict) -> None:
    get_client().table("talking_points").upsert(
        row, on_conflict="city_id,run_date,audience"
    ).execute()


def replace_active_listings(city_id: str, run_date: str, listings: list[dict]) -> None:
    client = get_client()
    # Drop this city's previous snapshot (any run_date) before inserting the
    # new one, so `active_listings` only ever holds the latest run per city.
    client.table("active_listings").delete().eq("city_id", city_id).execute()
    if listings:
        client.table("active_listings").insert(listings).execute()
