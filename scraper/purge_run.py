"""Deletes every row a single scrape run wrote.

For when a run writes bad data — the 2026-09-07 run wrote zeros for every
city after Realtor.com started returning 403, which the dashboard then
showed as a dip to zero on the trend charts.

Deliberately narrow: it takes one run_date and removes that date's rows
from the four data tables. It never touches `cities`, and it has no
default date — you have to say which run to purge.

    RUN_DATE=2026-09-07 python purge_run.py
"""

from __future__ import annotations

import logging
import os
import re
import sys

from db import get_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("market_trends.purge")

# `cities` is intentionally absent — it holds the city list, not run data.
TABLES = ("market_stats", "talking_points", "active_listings", "recent_sales")

DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def purge(run_date: str) -> dict[str, int]:
    client = get_client()
    deleted = {}
    for table in TABLES:
        # supabase-py returns the deleted rows, so len() is the real count
        # rather than an assumption about what matched.
        result = client.table(table).delete().eq("run_date", run_date).execute()
        deleted[table] = len(result.data or [])
        logger.info("  %s: deleted %d row(s)", table, deleted[table])
    return deleted


def main() -> int:
    run_date = (os.environ.get("RUN_DATE") or (sys.argv[1] if len(sys.argv) > 1 else "")).strip()

    if not run_date:
        logger.error("RUN_DATE is required (e.g. RUN_DATE=2026-09-07). Refusing to guess.")
        return 2
    if not DATE_PATTERN.match(run_date):
        logger.error("RUN_DATE must look like YYYY-MM-DD, got %r", run_date)
        return 2

    logger.info("Purging every row written for run_date=%s", run_date)
    deleted = purge(run_date)
    total = sum(deleted.values())

    if total == 0:
        logger.warning(
            "Nothing deleted — no rows exist for %s. Check the date; run_date is "
            "the UTC date the scrape ran.",
            run_date,
        )
    else:
        logger.info("Done. %d row(s) deleted across %d tables.", total, len(TABLES))
    return 0


if __name__ == "__main__":
    sys.exit(main())
