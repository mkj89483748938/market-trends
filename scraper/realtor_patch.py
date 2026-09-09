"""Keeps HomeHarvest working against Realtor.com's bot defenses.

HomeHarvest 0.8.18 (Dec 2025) is the newest release and upstream has been
quiet since, so when Realtor.com tightens its edge there is no version to
upgrade to — the adjustments have to live here.

On 2026-09-07 every request started coming back `403 Forbidden` at the
location-lookup step. HomeHarvest posts to Realtor.com's GraphQL endpoint
with `requests` and a fixed header set, and two things about that had gone
stale enough to look automated:

1. **Headers.** A pinned `rdc-client-version` and a Chrome 135 User-Agent
   (April 2025) that no real visitor still sends.
2. **TLS fingerprint.** `requests` has a distinctive TLS/JA3 handshake that
   doesn't match any browser. Header edits can't fix this — the connection
   is flagged before a single header is read. `curl_cffi` handles it by
   impersonating a real Chrome handshake.

Which of these is actually responsible can't be determined from here, so
both are addressed and `probe.py` reports which transport gets through.

Everything is env-overridable, because the fix for the *next* round of
this is likely a value change rather than a code change.
"""

from __future__ import annotations

import logging
import os

from homeharvest.core.scrapers import DEFAULT_HEADERS
from homeharvest.core.scrapers import realtor as realtor_module

logger = logging.getLogger("market_trends.realtor_patch")

# Bumping this is the cheapest first thing to try when 403s reappear. It is
# an estimate of a current Chrome, not a value read off a live browser — the
# point is that it isn't 17 months old, and that sec-ch-ua agrees with it
# (a mismatch between the two is itself a bot signal).
DEFAULT_CHROME_MAJOR = "140"

# Realtor.com's own web client version. Pinned by HomeHarvest at 3.0.2515;
# if they start rejecting old client versions this is the knob.
DEFAULT_RDC_CLIENT_VERSION = "3.0.2515"

# HomeHarvest passes no timeout to requests.post at all, so a hanging edge
# can stall a run indefinitely — the 2026-09-07 run took 39 minutes instead
# of the usual 11 for exactly this reason.
REQUEST_TIMEOUT_SECONDS = 30


def _chrome_major() -> str:
    return os.environ.get("SCRAPER_CHROME_MAJOR", DEFAULT_CHROME_MAJOR).strip() or DEFAULT_CHROME_MAJOR


def build_headers() -> dict[str, str]:
    """Header overrides, kept internally consistent with each other."""
    major = _chrome_major()
    user_agent = os.environ.get("SCRAPER_USER_AGENT") or (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        f"(KHTML, like Gecko) Chrome/{major}.0.0.0 Safari/537.36"
    )
    return {
        "User-Agent": user_agent,
        "sec-ch-ua": f'"Google Chrome";v="{major}", "Not-A.Brand";v="8", "Chromium";v="{major}"',
        "rdc-client-version": os.environ.get(
            "SCRAPER_RDC_CLIENT_VERSION", DEFAULT_RDC_CLIENT_VERSION
        ),
    }


class _ImpersonatingRequests:
    """Stands in for the `requests` module inside HomeHarvest.

    Only `.post` is needed — both call sites in HomeHarvest 0.8.18
    (`core/scrapers/__init__.py` and `core/scrapers/realtor/__init__.py`)
    use `requests.post`. curl_cffi's response exposes `.status_code` and
    `.json()`, which is all HomeHarvest touches.
    """

    def __init__(self, impersonate: str):
        from curl_cffi import requests as cffi_requests

        self._requests = cffi_requests
        self._impersonate = impersonate

    def post(self, url, **kwargs):
        kwargs.setdefault("impersonate", self._impersonate)
        kwargs.setdefault("timeout", REQUEST_TIMEOUT_SECONDS)
        return self._requests.post(url, **kwargs)

    def get(self, url, **kwargs):
        kwargs.setdefault("impersonate", self._impersonate)
        kwargs.setdefault("timeout", REQUEST_TIMEOUT_SECONDS)
        return self._requests.get(url, **kwargs)


class _TimeoutRequests:
    """Plain `requests`, but with a timeout HomeHarvest forgot to set."""

    def __init__(self):
        import requests

        self._requests = requests

    def post(self, url, **kwargs):
        kwargs.setdefault("timeout", REQUEST_TIMEOUT_SECONDS)
        return self._requests.post(url, **kwargs)

    def get(self, url, **kwargs):
        kwargs.setdefault("timeout", REQUEST_TIMEOUT_SECONDS)
        return self._requests.get(url, **kwargs)


def _install_transport(transport) -> None:
    """Swap the `requests` name inside HomeHarvest's modules.

    Both modules did `import requests` at module scope, so rebinding the
    attribute on each module object is what takes effect — patching the
    real `requests` package would be far more invasive.
    """
    import homeharvest.core.scrapers as scrapers_base

    realtor_module.requests = transport
    scrapers_base.requests = transport


def apply(use_impersonation: bool | None = None, impersonate: str = "chrome") -> str:
    """Applies header + transport patches. Returns the transport in use.

    `use_impersonation=None` means "use curl_cffi if it's installed",
    which is the behavior we want in CI: the dependency is declared, but a
    missing wheel degrades to plain requests rather than killing the run.
    """
    overrides = build_headers()
    DEFAULT_HEADERS.update(overrides)  # in-place: the realtor module holds this same dict
    logger.info(
        "realtor headers: UA=Chrome/%s rdc-client-version=%s",
        _chrome_major(),
        overrides["rdc-client-version"],
    )

    if use_impersonation is None:
        try:
            import curl_cffi  # noqa: F401
            use_impersonation = True
        except ImportError:
            use_impersonation = False
            logger.warning("curl_cffi not installed — falling back to plain requests")

    if use_impersonation:
        try:
            _install_transport(_ImpersonatingRequests(impersonate))
            logger.info("realtor transport: curl_cffi impersonating %s", impersonate)
            return f"curl_cffi:{impersonate}"
        except Exception:  # noqa: BLE001 - a broken curl_cffi shouldn't kill the run
            logger.exception("curl_cffi transport failed to install, using plain requests")

    _install_transport(_TimeoutRequests())
    logger.info("realtor transport: plain requests (timeout=%ss)", REQUEST_TIMEOUT_SECONDS)
    return "requests"


def get_proxy() -> str | None:
    """Optional outbound proxy for Realtor.com requests.

    If the block turns out to be on GitHub Actions' datacenter IP ranges
    rather than on our client signature, no amount of header or TLS work
    helps and requests have to leave from somewhere else. Set SCRAPER_PROXY
    to a proxy URL (a residential/ISP proxy is what these blocks are
    designed to not catch). Unset, this changes nothing.
    """
    proxy = os.environ.get("SCRAPER_PROXY", "").strip()
    return proxy or None
