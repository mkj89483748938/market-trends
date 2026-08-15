import logging
import time
from datetime import date, timedelta

import pandas as pd
from homeharvest import scrape_property

logger = logging.getLogger("market_trends.scrape")

SOLD_WINDOW_DAYS = 30
EMPTY_RETRY_PAUSE_SECONDS = 5


def _empty_df() -> pd.DataFrame:
    return pd.DataFrame()


def _scrape_once(**kwargs) -> pd.DataFrame:
    try:
        result = scrape_property(**kwargs)
        return result if result is not None else _empty_df()
    except Exception:  # noqa: BLE001 - one city's failure shouldn't kill the run
        logger.exception("scrape_property failed for %s", kwargs)
        return _empty_df()


def _safe_scrape(**kwargs) -> pd.DataFrame:
    """Scrapes with one retry if the first attempt comes back empty.

    An empty result for a real Orange County city is far more likely a
    transient blocked/empty response from Realtor.com than an actual zero —
    we've seen this hit both an active-listings query (Westminster showing
    0 active while 31 homes sold in the same 30 days) and a sold-listings
    query (Anaheim, one of the largest cities in the county, showing no
    90-day sold data). Retrying costs nothing when the result is
    legitimately small/empty (a real small city's 30-day sold count, say) —
    it just repeats and confirms it.
    """
    result = _scrape_once(**kwargs)
    if result.empty:
        logger.warning("scrape came back empty for %s, retrying once", kwargs)
        time.sleep(EMPTY_RETRY_PAUSE_SECONDS)
        result = _scrape_once(**kwargs)
    return result


# Whatever realtor.com gives us to identify a listing by, best first. Not all
# of these are present on every response, so we try them in order.
_ID_COLUMNS = ("property_id", "listing_id", "mls_id", "property_url")

# Statuses inside the for_sale feed that mean "already under contract".
# CONTINGENT is deliberately not here — a contingent listing is still taking
# backup offers and still counts as available in the reports agents compare
# us against.
_UNDER_CONTRACT_TOKENS = ("PENDING", "UNDER_CONTRACT")


def _listing_keys(df: pd.DataFrame) -> tuple[str, set] | tuple[None, set]:
    for column in _ID_COLUMNS:
        if df is not None and column in df.columns:
            keys = set(df[column].dropna().astype(str))
            if keys:
                return column, keys
    return None, set()


def exclude_pending(active: pd.DataFrame, pending: pd.DataFrame) -> pd.DataFrame:
    """Removes under-contract homes from the active-inventory frame.

    Realtor.com's `for_sale` feed carries some listings that are already in
    escrow, which inflates active inventory and — because months of supply is
    inventory divided by sales pace — inflates that too. Two passes: drop
    anything the feed itself flags as pending/under contract, then drop
    anything that also shows up in the dedicated `pending` query.

    A buyer can't go buy a home that's in escrow, so counting it as available
    overstates their choices and understates the seller's position.
    """
    if active is None or active.empty:
        return active

    before = len(active)
    cleaned = active

    if "status" in cleaned.columns:
        status = cleaned["status"].astype(str).str.upper()
        flagged = status.apply(lambda s: any(tok in s for tok in _UNDER_CONTRACT_TOKENS))
        cleaned = cleaned[~flagged]

    column, pending_keys = _listing_keys(pending)
    if column and column in cleaned.columns:
        overlap = cleaned[column].astype(str).isin(pending_keys)
        cleaned = cleaned[~overlap]

    removed = before - len(cleaned)
    if removed:
        logger.info(
            "  removed %d under-contract listing(s) from active inventory (%d -> %d)",
            removed,
            before,
            len(cleaned),
        )
    return cleaned


def fetch_city_data(location: str) -> dict[str, pd.DataFrame]:
    """Fetches everything needed to compute one city's stats for one run."""
    today = date.today()

    recent_from = today - timedelta(days=SOLD_WINDOW_DAYS)
    trailing_90d_from = today - timedelta(days=90)

    last_year_to = today - timedelta(days=365)
    last_year_from = last_year_to - timedelta(days=SOLD_WINDOW_DAYS)

    active = _safe_scrape(location=location, listing_type="for_sale", limit=10000)
    pending = _safe_scrape(location=location, listing_type="pending", limit=10000)
    sold_recent = _safe_scrape(
        location=location, listing_type="sold", date_from=str(recent_from), date_to=str(today), limit=10000
    )
    # A wider trailing baseline (vs. an adjacent 30-day window) so the
    # "recent price trend" figure isn't as whipsawed by which specific
    # homes happened to close in any one short window.
    sold_90d = _safe_scrape(
        location=location, listing_type="sold", date_from=str(trailing_90d_from), date_to=str(today), limit=10000
    )
    sold_last_year = _safe_scrape(
        location=location,
        listing_type="sold",
        date_from=str(last_year_from),
        date_to=str(last_year_to),
        limit=10000,
    )

    return {
        "active": exclude_pending(active, pending),
        "pending": pending,
        "sold_recent": sold_recent,
        "sold_90d": sold_90d,
        "sold_last_year": sold_last_year,
    }
