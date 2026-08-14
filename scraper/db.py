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
