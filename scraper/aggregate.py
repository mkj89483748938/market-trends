import logging
from datetime import date, timedelta

import pandas as pd

logger = logging.getLogger("market_trends.aggregate")

# Property-type segments, mirroring how Altos/BHHS market reports split
# Houses vs. Condos/Co-Op. Mixing all types into one number made our figures
# look wrong beside those reports in condo-heavy cities.
SEGMENT_ALL = "all"
SEGMENT_SINGLE_FAMILY = "single_family"
SEGMENT_CONDO_TOWNHOME = "condo_townhome"
SEGMENTS = (SEGMENT_ALL, SEGMENT_SINGLE_FAMILY, SEGMENT_CONDO_TOWNHOME)

# Substring matching rather than an exact enum list: HomeHarvest passes
# realtor.com's property-type values through (SINGLE_FAMILY, CONDOS,
# CONDO_TOWNHOME_ROWHOME_COOP, TOWNHOMES, ...) and that vocabulary can shift.
# Anything unmatched (land, mobile, multi-family, farm) still counts toward
# `all` but lands in neither sub-segment — same as Altos excluding land from
# its Houses tab.
_SINGLE_FAMILY_TOKENS = ("SINGLE_FAMILY",)
_CONDO_TOKENS = ("CONDO", "TOWNHOME", "TOWNHOUSE", "COOP", "CO_OP", "APARTMENT")


def _style_series(df: pd.DataFrame) -> pd.Series | None:
    if df is None or df.empty or "style" not in df.columns:
        return None
    return df["style"].astype(str).str.upper()


def segment_frame(df: pd.DataFrame, segment: str) -> pd.DataFrame:
    """Filters a listings dataframe down to one property-type segment."""
    if segment == SEGMENT_ALL:
        return df

    styles = _style_series(df)
    if styles is None:
        # No style column (or no rows) — can't segment, so report empty
        # rather than silently passing the unfiltered frame through as if
        # it were single-family-only.
        return df.iloc[0:0] if df is not None else df

    if segment == SEGMENT_SINGLE_FAMILY:
        tokens = _SINGLE_FAMILY_TOKENS
    else:
        tokens = _CONDO_TOKENS

    mask = styles.apply(lambda s: any(tok in s for tok in tokens))
    return df[mask]


def log_style_distribution(city_name: str, active: pd.DataFrame) -> None:
    """One-line record of the raw style values seen, so the segment rules can
    be checked against reality instead of assumed."""
    styles = _style_series(active)
    if styles is None:
        logger.warning("  %s: no 'style' column available to segment on", city_name)
        return
    counts = styles.value_counts().to_dict()
    logger.info("  %s active-listing styles: %s", city_name, counts)


def _median(df: pd.DataFrame, column: str) -> float | None:
    if column not in df.columns:
        return None
    series = pd.to_numeric(df[column], errors="coerce").dropna()
    return float(series.median()) if len(series) else None


def _mean(df: pd.DataFrame, column: str) -> float | None:
    if column not in df.columns:
        return None
    series = pd.to_numeric(df[column], errors="coerce").dropna()
    return float(series.mean()) if len(series) else None


def _count(df: pd.DataFrame) -> int:
    return int(len(df)) if df is not None else 0


def _pct_change(new: float | None, old: float | None) -> float | None:
    if new is None or old in (None, 0):
        return None
    return round((new - old) / old * 100, 1)


def _sold_to_list_ratio(df: pd.DataFrame) -> float | None:
    if not {"sold_price", "list_price"}.issubset(df.columns):
        return None
    sold = pd.to_numeric(df["sold_price"], errors="coerce")
    listed = pd.to_numeric(df["list_price"], errors="coerce")
    valid = (sold.notna()) & (listed.notna()) & (listed != 0)
    if not valid.any():
        return None
    ratio = (sold[valid] / listed[valid]) * 100
    return round(float(ratio.median()), 1)


def _new_listings_count(active: pd.DataFrame, run_date: str, days: int) -> int | None:
    if active is None or "list_date" not in active.columns:
        if active is not None:
            logger.warning(
                "no 'list_date' column in active listings; available columns: %s",
                list(active.columns),
            )
        return None
    list_dates = pd.to_datetime(active["list_date"], errors="coerce")
    cutoff = pd.Timestamp(run_date) - pd.Timedelta(days=days)
    return int((list_dates >= cutoff).sum())


def _months_of_supply(active_inventory: int | None, homes_sold_30d: int | None) -> float | None:
    if active_inventory is None or not homes_sold_30d:
        return None
    return round(active_inventory / homes_sold_30d, 1)


def _nearest_history(history: list[dict], target: date, tolerance_days: int) -> dict | None:
    """Closest prior market_stats row to `target`, within `tolerance_days`.

    Weekly runs won't land on an exact 30/365-day mark, so this picks
    whichever past row is closest to the target date instead of requiring
    an exact match.
    """
    best, best_diff = None, None
    for row in history:
        row_date = date.fromisoformat(row["run_date"])
        diff = abs((row_date - target).days)
        if diff <= tolerance_days and (best_diff is None or diff < best_diff):
            best, best_diff = row, diff
    return best


def build_market_stats(
    city_id: str,
    run_date: str,
    data: dict[str, pd.DataFrame],
    history: list[dict],
    segment: str = SEGMENT_ALL,
) -> dict:
    active = segment_frame(data["active"], segment)
    pending = segment_frame(data["pending"], segment)
    sold_recent = segment_frame(data["sold_recent"], segment)
    sold_90d = segment_frame(data["sold_90d"], segment)
    sold_last_year = segment_frame(data["sold_last_year"], segment)

    pending_count = _count(pending)
    active_inventory = _count(active)
    median_list_price = _median(active, "list_price")
    avg_list_price = _mean(active, "list_price")
    median_price_per_sqft = _median(active, "price_per_sqft")
    median_dom = _median(active, "days_on_mls")
    new_listings_7d = _new_listings_count(active, run_date, 7)
    new_listings_30d = _new_listings_count(active, run_date, 30)

    homes_sold_30d = _count(sold_recent)
    median_sold_price = _median(sold_recent, "sold_price")
    sold_to_list_ratio = _sold_to_list_ratio(sold_recent)
    months_of_supply = _months_of_supply(active_inventory, homes_sold_30d)

    median_sold_price_90d = _median(sold_90d, "sold_price")
    median_sold_price_last_year = _median(sold_last_year, "sold_price")
    homes_sold_last_year = _count(sold_last_year)
    median_dom_last_year = _median(sold_last_year, "days_on_mls")

    # Realtor.com has no "active inventory a year ago" query — only a live
    # snapshot exists — so these compare against our own accumulated history
    # instead, and stay None until enough weekly runs have happened.
    today = date.fromisoformat(run_date)
    prior_30d = _nearest_history(history, today - timedelta(days=30), tolerance_days=10)
    prior_365d = _nearest_history(history, today - timedelta(days=365), tolerance_days=20)

    return {
        "city_id": city_id,
        "run_date": run_date,
        "property_segment": segment,
        "active_inventory": active_inventory,
        "new_listings_7d": new_listings_7d,
        "new_listings_30d": new_listings_30d,
        "pending_count": pending_count,
        "months_of_supply": months_of_supply,
        "median_list_price": median_list_price,
        "avg_list_price": avg_list_price,
        "median_price_per_sqft": median_price_per_sqft,
        "median_dom": median_dom,
        "homes_sold_30d": homes_sold_30d,
        "median_sold_price": median_sold_price,
        "sold_to_list_ratio": sold_to_list_ratio,
        # Retired: "MoM" (adjacent 30-day windows) was noisy for smaller
        # sample sizes — this column stays in the schema but is no longer
        # written to. price_change_vs_90d replaces it.
        "price_change_mom": None,
        "price_change_vs_90d": _pct_change(median_sold_price, median_sold_price_90d),
        "price_change_yoy": _pct_change(median_sold_price, median_sold_price_last_year),
        "inventory_change_mom": _pct_change(
            active_inventory, prior_30d["active_inventory"] if prior_30d else None
        ),
        "inventory_change_yoy": _pct_change(
            active_inventory, prior_365d["active_inventory"] if prior_365d else None
        ),
        "homes_sold_change_yoy": _pct_change(homes_sold_30d, homes_sold_last_year),
        "dom_change_yoy": _pct_change(median_dom, median_dom_last_year),
    }


def build_active_listings(
    city_id: str,
    run_date: str,
    active: pd.DataFrame,
    segment: str = SEGMENT_ALL,
    limit: int = 25,
) -> list[dict]:
    active = segment_frame(active, segment)
    if active is None or active.empty:
        return []

    df = active.copy()
    # Most-recently-listed first (lowest days-on-market) — this feeds the
    # "Recent active listings" table, so what gets stored here should match
    # what that label actually promises, not e.g. the priciest listings.
    if "days_on_mls" in df.columns:
        df = df.sort_values("days_on_mls", ascending=True, na_position="last")
    elif "list_price" in df.columns:
        df = df.sort_values("list_price", ascending=False)
    df = df.head(limit)

    rows = []
    for _, row in df.iterrows():
        address_parts = [row.get("street"), row.get("unit"), row.get("city"), row.get("state")]
        address = ", ".join(str(p) for p in address_parts if pd.notna(p) and str(p).strip())

        rows.append(
            {
                "city_id": city_id,
                "run_date": run_date,
                "property_segment": segment,
                "address": address or None,
                "list_price": _to_float(row.get("list_price")),
                "beds": _to_float(row.get("beds")),
                "baths": _to_float(row.get("full_baths")),
                "sqft": _to_float(row.get("sqft")),
                "days_on_market": _to_int(row.get("days_on_mls")),
                "property_url": row.get("property_url") if pd.notna(row.get("property_url")) else None,
            }
        )
    return rows


def _to_float(value) -> float | None:
    try:
        if value is None or pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value) -> int | None:
    parsed = _to_float(value)
    return int(parsed) if parsed is not None else None
