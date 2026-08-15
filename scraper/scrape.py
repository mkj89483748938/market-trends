import logging
from datetime import date, timedelta

import pandas as pd
from homeharvest import scrape_property

logger = logging.getLogger("market_trends.scrape")

SOLD_WINDOW_DAYS = 30


def _empty_df() -> pd.DataFrame:
    return pd.DataFrame()


def _safe_scrape(**kwargs) -> pd.DataFrame:
    try:
        result = scrape_property(**kwargs)
        return result if result is not None else _empty_df()
    except Exception:  # noqa: BLE001 - one city's failure shouldn't kill the run
        logger.exception("scrape_property failed for %s", kwargs)
        return _empty_df()


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
        "active": active,
        "pending": pending,
        "sold_recent": sold_recent,
        "sold_90d": sold_90d,
        "sold_last_year": sold_last_year,
    }
