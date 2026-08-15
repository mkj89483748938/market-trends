import pandas as pd


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


def build_market_stats(city_id: str, run_date: str, data: dict[str, pd.DataFrame]) -> dict:
    active = data["active"]
    sold_recent = data["sold_recent"]
    sold_prior = data["sold_prior"]
    sold_last_year = data["sold_last_year"]

    active_inventory = _count(active)
    median_list_price = _median(active, "list_price")
    avg_list_price = _mean(active, "list_price")
    median_price_per_sqft = _median(active, "price_per_sqft")
    median_dom = _median(active, "days_on_mls")

    homes_sold_30d = _count(sold_recent)
    median_sold_price = _median(sold_recent, "sold_price")
    sold_to_list_ratio = _sold_to_list_ratio(sold_recent)

    median_sold_price_prior = _median(sold_prior, "sold_price")
    median_sold_price_last_year = _median(sold_last_year, "sold_price")
    inventory_last_year = _count(sold_last_year)
    median_dom_last_year = _median(sold_last_year, "days_on_mls")

    return {
        "city_id": city_id,
        "run_date": run_date,
        "active_inventory": active_inventory,
        "new_listings_30d": None,
        "median_list_price": median_list_price,
        "avg_list_price": avg_list_price,
        "median_price_per_sqft": median_price_per_sqft,
        "median_dom": median_dom,
        "homes_sold_30d": homes_sold_30d,
        "median_sold_price": median_sold_price,
        "sold_to_list_ratio": sold_to_list_ratio,
        "price_change_mom": _pct_change(median_sold_price, median_sold_price_prior),
        "price_change_yoy": _pct_change(median_sold_price, median_sold_price_last_year),
        "inventory_change_mom": None,
        "inventory_change_yoy": _pct_change(homes_sold_30d, inventory_last_year),
        "dom_change_yoy": _pct_change(median_dom, median_dom_last_year),
    }


def build_active_listings(city_id: str, run_date: str, active: pd.DataFrame, limit: int = 25) -> list[dict]:
    if active is None or active.empty:
        return []

    df = active.copy()
    if "list_price" in df.columns:
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
