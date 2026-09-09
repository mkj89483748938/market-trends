"""Tests which transport, if any, can reach Realtor.com right now.

Runs one cheap location lookup per strategy and prints the result, so a
one-minute job answers "are we still blocked, and does the fix work?"
instead of inferring it from a 40-minute scrape.

    python probe.py

Exits non-zero if nothing works, so it reads as a red X in Actions.
"""

from __future__ import annotations

import logging
import os
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("market_trends.probe")

PROBE_LOCATION = "Irvine, CA"


def _try(label: str, use_impersonation: bool | None, use_proxy: bool) -> tuple[str, str]:
    """Returns (label, outcome). Never raises — every strategy gets a turn."""
    # Re-import per attempt so the patch is applied to a fresh module state.
    for name in list(sys.modules):
        if name.startswith("homeharvest") or name in ("realtor_patch", "scrape"):
            del sys.modules[name]

    import realtor_patch
    from homeharvest import scrape_property

    try:
        realtor_patch.apply(use_impersonation=use_impersonation)
    except Exception as exc:  # noqa: BLE001
        return label, f"PATCH FAILED: {type(exc).__name__}: {exc}"

    kwargs = {"location": PROBE_LOCATION, "listing_type": "for_sale", "limit": 5}
    if use_proxy:
        proxy = realtor_patch.get_proxy()
        if not proxy:
            return label, "SKIPPED (SCRAPER_PROXY not set)"
        kwargs["proxy"] = proxy

    try:
        result = scrape_property(**kwargs)
        count = 0 if result is None else len(result)
        if count > 0:
            return label, f"OK — {count} listing(s) returned"
        return label, "EMPTY — request succeeded but returned no rows"
    except Exception as exc:  # noqa: BLE001
        return label, f"FAILED: {type(exc).__name__}: {str(exc)[:120]}"


def main() -> int:
    logger.info("Probing Realtor.com access with location=%r", PROBE_LOCATION)
    logger.info(
        "Chrome major=%s, proxy=%s",
        os.environ.get("SCRAPER_CHROME_MAJOR", "default"),
        "set" if os.environ.get("SCRAPER_PROXY") else "not set",
    )

    results = [
        _try("plain requests (HomeHarvest stock behavior)", False, False),
        _try("curl_cffi Chrome impersonation", True, False),
        _try("curl_cffi + SCRAPER_PROXY", True, True),
    ]

    print("\n=== Realtor.com probe results ===")
    for label, outcome in results:
        print(f"  {label:45} {outcome}")
    print()

    if any(outcome.startswith("OK") for _, outcome in results):
        logger.info("At least one transport works — the scraper can run.")
        return 0

    logger.error(
        "Every transport failed. If all show 403, the block is on our client "
        "signature or on this runner's IP range; a residential proxy in "
        "SCRAPER_PROXY is the remaining lever."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
