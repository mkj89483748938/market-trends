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


def _try(label: str, patch: str, use_proxy: bool) -> tuple[str, str]:
    """Returns (label, outcome). Never raises — every strategy gets a turn.

    `patch` is one of:
      "none"        — HomeHarvest exactly as shipped, no patching at all.
                      This is the control: if it passes, whatever was
                      blocking us has lifted on its own and our patches
                      aren't what's carrying the run.
      "headers"     — refreshed headers, HomeHarvest's own `requests`.
      "impersonate" — refreshed headers plus a Chrome TLS handshake.
    """
    # Re-import per attempt so each starts from unpatched module state —
    # otherwise a previous attempt's patch leaks into this one and every
    # row reports on the same configuration.
    for name in list(sys.modules):
        if name.startswith("homeharvest") or name in ("realtor_patch", "scrape"):
            del sys.modules[name]

    import realtor_patch
    from homeharvest import scrape_property

    if patch != "none":
        try:
            realtor_patch.apply(use_impersonation=(patch == "impersonate"))
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
        _try("unpatched HomeHarvest (control)", "none", False),
        _try("refreshed headers, plain requests", "headers", False),
        _try("refreshed headers + Chrome TLS handshake", "impersonate", False),
        _try("refreshed headers + TLS + SCRAPER_PROXY", "impersonate", True),
    ]

    print("\n=== Realtor.com probe results ===")
    for label, outcome in results:
        print(f"  {label:42} {outcome}")
    print()

    control_ok = results[0][1].startswith("OK")
    if any(outcome.startswith("OK") for _, outcome in results):
        if control_ok:
            logger.info(
                "The unpatched control passed, so Realtor.com is not blocking "
                "us at all right now — the patches aren't what's carrying the "
                "run, and this tells us nothing about whether they'd help."
            )
        else:
            logger.info("Patched transports work; the unpatched control does not.")
        return 0

    logger.error(
        "Every transport failed. If all show 403, the block is on our client "
        "signature or on this runner's IP range; a residential proxy in "
        "SCRAPER_PROXY is the remaining lever."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
