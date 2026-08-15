"""One-off backfill: populates historical median-sold-price data so the
trend chart has real history from day one, instead of waiting for weekly
runs to accumulate it.

Only sold-price-based fields can be backfilled this way — Realtor.com only
exposes a *live* snapshot of active inventory/list price, not a historical
one, so those fields stay None on backfilled rows and fill in naturally as
main.py runs weekly going forward.

Run once via the "Backfill sold-price history" GitHub Actions workflow
(workflow_dispatch), or locally: python backfill.py [months, default 6]
"""

import logging
import sys
import time
from datetime import date, timedelta

from aggregate import SEGMENTS, _count, _median, segment_frame
from cities import CITIES, query_location
from db import ensure_cities, upsert_market_stats
from scrape import _safe_scrape

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("market_trends.backfill")

DEFAULT_MONTHS = 6
WINDOW_DAYS = 30
PAUSE_SECONDS = 3


def backfill_city(city_id: str, city_name: str, months: int) -> None:
    location = query_location(city_name)
    today = date.today()

    for month_offset in range(1, months + 1):
        window_to = today - timedelta(days=WINDOW_DAYS * (month_offset - 1))
        window_from = today - timedelta(days=WINDOW_DAYS * month_offset)
        run_date = window_from  # stable, unique per offset, always in the past

        sold = _safe_scrape(
            location=location,
            listing_type="sold",
            date_from=str(window_from),
            date_to=str(window_to),
            limit=10000,
        )

        for segment in SEGMENTS:
            sold_seg = segment_frame(sold, segment)
            row = {
                "city_id": city_id,
                "run_date": str(run_date),
                "property_segment": segment,
                "homes_sold_30d": _count(sold_seg),
                "median_sold_price": _median(sold_seg, "sold_price"),
            }
            upsert_market_stats(row)
            logger.info(
                "  %s to %s [%s] -> %s sold, median $%s",
                window_from,
                window_to,
                segment,
                row["homes_sold_30d"],
                row["median_sold_price"],
            )
        time.sleep(PAUSE_SECONDS)


def run(months: int = DEFAULT_MONTHS) -> None:
    logger.info("Backfilling %d months of sold-price history for %d cities", months, len(CITIES))
    city_ids = ensure_cities(CITIES)

    for i, city in enumerate(CITIES):
        city_id = city_ids.get(city["slug"])
        if not city_id:
            logger.error("No city_id for %s, skipping", city["name"])
            continue
        logger.info("[%d/%d] %s", i + 1, len(CITIES), city["name"])
        try:
            backfill_city(city_id, city["name"], months)
        except Exception:  # noqa: BLE001 - keep going for the remaining cities
            logger.exception("Backfill failed for %s", city["name"])

    logger.info("Done.")


if __name__ == "__main__":
    months_arg = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_MONTHS
    run(months_arg)
