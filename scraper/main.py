import logging
import time
from datetime import date

import pandas as pd

from aggregate import (
    SEGMENT_ALL,
    SEGMENTS,
    build_active_listings,
    build_market_stats,
    build_recent_sales,
    log_style_distribution,
)
from cities import CITIES, COUNTY, query_location
from db import (
    ensure_cities,
    get_stats_history,
    replace_active_listings,
    replace_recent_sales,
    upsert_market_stats,
    upsert_talking_points,
    upsert_text_messages,
)
from scrape import fetch_city_data, is_empty_result
from talking_points import generate_talking_points
from text_messages import generate_text_messages

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("market_trends.main")

PAUSE_BETWEEN_CITIES_SECONDS = 5

# A city or two failing is normal noise; a third of the county failing is an
# outage and the run should go red instead of reporting success.
FAIL_RUN_ABOVE_SKIP_RATIO = 0.33

# The county rollup is only published when nearly every city contributed. A
# "county median" computed from 25 of 34 cities isn't wrong by a little — it
# silently omits whole markets, and nothing on the page would say so. Better
# to leave last week's county row standing than to publish a partial one.
COUNTY_MIN_CITY_COVERAGE = 0.9

# The frames pooled across cities to build the county view.
FRAME_KEYS = ("active", "pending", "sold_recent", "sold_90d", "sold_last_year")

# Which locations get suggested follow-up texts. None means every city plus
# the county rollup. Piloted on Orange first and reviewed there before going
# county-wide, since these are messages agents send to real leads. Set this
# back to a tuple of slugs to narrow it again.
TEXT_MESSAGE_SLUGS: tuple[str, ...] | None = None


def write_location(city_id: str, name: str, slug: str, run_date: str, data: dict) -> None:
    """Builds and stores every row for one location (a city or the county).

    The county rollup goes through this same function rather than a parallel
    implementation, so its stats are computed by exactly the code the city
    stats are — no chance of the two definitions drifting apart.
    """
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
    points = generate_talking_points(name, all_segment_stats[SEGMENT_ALL])
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

    # Follow-up texts, currently limited to the cities being piloted so the
    # wording can be approved before agents send it to real leads.
    if TEXT_MESSAGE_SLUGS is None or slug in TEXT_MESSAGE_SLUGS:
        messages = generate_text_messages(name, all_segment_stats[SEGMENT_ALL])
        if messages:
            for audience in ("buyer", "seller"):
                upsert_text_messages(
                    {
                        "city_id": city_id,
                        "run_date": run_date,
                        "audience": audience,
                        "messages": messages[audience],
                    }
                )
            logger.info(
                "  wrote %d buyer / %d seller follow-up text(s)",
                len(messages["buyer"]),
                len(messages["seller"]),
            )


def build_county_data(pooled: dict[str, list[pd.DataFrame]]) -> dict[str, pd.DataFrame]:
    """Concatenates every contributing city's frames into one county frame.

    Pooling the raw listings (rather than averaging the cities' summary
    numbers) is what makes the county medians real medians. A median of 34
    city medians is not the county's median — it weights Villa Park's 17
    listings the same as Irvine's 849.
    """
    return {
        key: pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        for key, frames in pooled.items()
    }


def _write_county(
    run_date: str,
    city_ids: dict[str, str],
    pooled: dict[str, list[pd.DataFrame]],
    contributed: int,
) -> None:
    county_id = city_ids.get(COUNTY["slug"])
    if not county_id:
        logger.error("No city_id for %s, skipping county rollup", COUNTY["name"])
        return

    coverage = contributed / len(CITIES) if CITIES else 0
    if coverage < COUNTY_MIN_CITY_COVERAGE:
        logger.warning(
            "County rollup skipped: only %d/%d cities contributed (%.0f%%, need %.0f%%). "
            "A county number missing whole cities would read as real on the page.",
            contributed,
            len(CITIES),
            coverage * 100,
            COUNTY_MIN_CITY_COVERAGE * 100,
        )
        return

    logger.info("[county] %s — pooling %d cities", COUNTY["name"], contributed)
    try:
        county_data = build_county_data(pooled)
        logger.info(
            "  pooled counts: active=%d pending=%d sold_recent=%d sold_90d=%d sold_last_year=%d",
            len(county_data["active"]),
            len(county_data["pending"]),
            len(county_data["sold_recent"]),
            len(county_data["sold_90d"]),
            len(county_data["sold_last_year"]),
        )
        write_location(county_id, COUNTY["name"], COUNTY["slug"], run_date, county_data)
    except Exception:  # noqa: BLE001 - the city rows are already written and valid
        logger.exception("Failed building the county rollup")


def run() -> None:
    run_date = str(date.today())
    logger.info("Starting market-trends scrape for run_date=%s", run_date)

    city_ids = ensure_cities(CITIES + [COUNTY])
    skipped: list[str] = []
    pooled: dict[str, list[pd.DataFrame]] = {key: [] for key in FRAME_KEYS}
    contributed = 0

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

            write_location(city_id, city["name"], city["slug"], run_date, data)

            # Keep this city's listings for the county rollup. Done after the
            # write so a city that fails partway through doesn't contribute a
            # half-processed frame to the county total.
            for key in FRAME_KEYS:
                pooled[key].append(data[key])
            contributed += 1
        except Exception:  # noqa: BLE001 - keep going for the remaining cities
            logger.exception("Failed processing %s", city["name"])
            skipped.append(city["name"])
        finally:
            # In a `finally` so the pause still happens on the skip path above.
            time.sleep(PAUSE_BETWEEN_CITIES_SECONDS)

    _write_county(run_date, city_ids, pooled, contributed)

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
