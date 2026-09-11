"""Regenerates follow-up texts from stats already in the database.

The full scrape takes ~11 minutes and re-reads all 34 cities from
Realtor.com. When only the *wording* is being iterated on, none of that is
needed — the market numbers are already stored. This reruns just the text
generation against the latest stored stats: one API call per city, a few
seconds, and no load on Realtor.com.

It also prints every generated message, so the wording can be reviewed from
the run log without opening the dashboard.

    python regen_texts.py           # the cities in TEXT_MESSAGE_SLUGS
    TEXT_SLUGS=orange,irvine python regen_texts.py
"""

from __future__ import annotations

import logging
import os
import sys

from cities import CITIES, COUNTY
from db import ensure_cities, get_latest_stats, upsert_text_messages
from main import TEXT_MESSAGE_SLUGS
from text_messages import MAX_MESSAGE_CHARS, _format_sms_stats, generate_text_messages

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("market_trends.regen_texts")


def _target_slugs() -> list[str]:
    override = os.environ.get("TEXT_SLUGS", "").strip()
    if override:
        return [s.strip() for s in override.split(",") if s.strip()]
    if TEXT_MESSAGE_SLUGS is None:
        return [c["slug"] for c in CITIES] + [COUNTY["slug"]]
    return list(TEXT_MESSAGE_SLUGS)


def main() -> int:
    slugs = _target_slugs()
    logger.info("Regenerating follow-up texts for: %s", ", ".join(slugs))

    by_slug = {c["slug"]: c["name"] for c in CITIES + [COUNTY]}
    city_ids = ensure_cities(CITIES + [COUNTY])

    failures = 0
    for slug in slugs:
        name = by_slug.get(slug)
        city_id = city_ids.get(slug)
        if not name or not city_id:
            logger.error("Unknown slug %r — skipping", slug)
            failures += 1
            continue

        stats = get_latest_stats(city_id)
        if not stats:
            logger.error("No stored stats for %s — run the scraper first", name)
            failures += 1
            continue

        logger.info("%s (stats from %s)", name, stats.get("run_date"))
        logger.info("  payload sent to Claude:\n%s", _format_sms_stats(stats))

        messages = generate_text_messages(name, stats)
        if not messages:
            failures += 1
            continue

        for audience in ("buyer", "seller"):
            upsert_text_messages(
                {
                    "city_id": city_id,
                    "run_date": stats["run_date"],
                    "audience": audience,
                    "messages": messages[audience],
                }
            )

        # Printed so the wording is reviewable straight from the run log.
        print(f"\n=== {name} — follow-up texts ===")
        for audience in ("buyer", "seller"):
            print(f"\n  {audience.upper()}")
            for i, message in enumerate(messages[audience], 1):
                flag = "  <-- OVER LIMIT" if len(message) > MAX_MESSAGE_CHARS else ""
                print(f"   {i}. {message}")
                print(f"      [{len(message)} chars]{flag}")
        print()

    if failures:
        logger.error("%d of %d location(s) failed", failures, len(slugs))
        return 1
    logger.info("Done. %d location(s) regenerated.", len(slugs))
    return 0


if __name__ == "__main__":
    sys.exit(main())
