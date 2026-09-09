import logging
import time
from datetime import date

from aggregate import (
    SEGMENT_ALL,
    SEGMENTS,
    build_active_listings,
    build_market_stats,
    build_recent_sales,
    log_style_distribution,
)
from cities import CITIES, query_location
from db import (
    ensure_cities,
    get_stats_history,
    replace_active_listings,
    replace_recent_sales,
    upsert_market_stats,
    upsert_talking_points,
)
from scrape import fetch_city_data, is_empty_result
from talking_points import generate_talking_points

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("market_trends.main")

PAUSE_BETWEEN_CITIES_SECONDS = 5

# A city or two failing is normal noise; a third of the county failing is an
# outage and the run should go red instead of reporting success.
FAIL_RUN_ABOVE_SKIP_RATIO = 0.33


def run() -> None:
    run_date = str(date.today())
    logger.info("Starting market-trends scrape for run_date=%s", run_date)

    city_ids = ensure_cities(CITIES)
    skipped: list[str] = []

    for i, city in enumerate(CITIES):
        city_id = city_ids.get(city["slug"])
        if not city_id:
            logger.error("No city_id for %s, skipping", city["name"])
            skipped.append(city["name"])
            continue

        logger.info("[%d/%d] %s", i + 1, len(CITIES), city["name"])

        try:
            data = fetch_city_data(query_location(city["name"]))
            logger.info(
                "  raw counts: active=%d pending=%d sold_recent=%d sold_90d=%d sold_last_year=%d",
                len(data["active"]),
                len(data["pending"]),
                len(data["sold_recent"]),
                len(data["sold_90d"]),
                len(data["sold_last_year"]),
            )
            # An upstream outage (Realtor.com started returning 403 to
            # HomeHarvest on 2026-09-07) makes every frame come back empty.
            # Writing that through produces a row of zeros that becomes the
            # newest row for the city — and since the dashboard reads the
            # newest row, one bad run blanks the whole site while perfectly
            # good data from last week sits underneath. Skip instead: stale
            # numbers with an honest "last updated" date beat zeros.
            if is_empty_result(data):
                logger.error(
                    "  %s: every query came back empty — skipping so last "
                    "good data stays live (blocked upstream?)",
                    city["name"],
                )
                skipped.append(city["name"])
                continue

            log_style_distribution(city["name"], data["active"])

            # One stats row per property segment, so the dashboard can be
            # reconciled against segment-split reports (Altos/BHHS "Houses"
            # vs. "Condos") instead of only showing a blended all-types number.
            all_segment_stats = {}
            listings: list[dict] = []
            sales: list[dict] = []
            for segment in SEGMENTS:
                history = get_stats_history(city_id, segment)
                stats = build_market_stats(city_id, run_date, data, history, segment)
                all_segment_stats[segment] = stats
                logger.info(
                    "  [%s] inventory=%s median_list=%s median_sold=%s vs90d=%s",
                    segment,
                    stats["active_inventory"],
                    stats["median_list_price"],
                    stats["median_sold_price"],
                    stats["price_change_vs_90d"],
                )
                upsert_market_stats(stats)
                listings.extend(build_active_listings(city_id, run_date, data["active"], segment))
                sales.extend(build_recent_sales(city_id, run_date, data["sold_recent"], segment))

            replace_active_listings(city_id, listings)
            replace_recent_sales(city_id, sales)
            logger.info("  wrote %d active listing(s), %d recent sale(s)", len(listings), len(sales))

            # Talking points are generated from the all-types view, matching
            # the dashboard's default segment.
            points = generate_talking_points(city["name"], all_segment_stats[SEGMENT_ALL])
            if points:
                for audience in ("buyer", "seller"):
                    upsert_talking_points(
                        {
                            "city_id": city_id,
                            "run_date": run_date,
                            "audience": audience,
                            "points": points[audience],
                        }
                    )
        except Exception:  # noqa: BLE001 - keep going for the remaining cities
            logger.exception("Failed processing %s", city["name"])
            skipped.append(city["name"])
        finally:
            # In a `finally` so the pause still happens on the skip path above.
            time.sleep(PAUSE_BETWEEN_CITIES_SECONDS)

    if skipped:
        logger.warning("Skipped %d/%d cities: %s", len(skipped), len(CITIES), ", ".join(skipped))
    logger.info("Done. %d/%d cities written.", len(CITIES) - len(skipped), len(CITIES))

    # Fail the job when a large share of cities came up empty. Previously a
    # run that scraped nothing at all still reported "success", so the first
    # sign of an outage was someone opening the dashboard and finding it
    # blank. A red X and the failure email are the point.
    if len(skipped) > len(CITIES) * FAIL_RUN_ABOVE_SKIP_RATIO:
        raise SystemExit(
            f"{len(skipped)} of {len(CITIES)} cities produced no data — "
            "treating this run as failed rather than reporting success."
        )


if __name__ == "__main__":
    run()
