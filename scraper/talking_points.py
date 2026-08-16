import json
import logging
import os
import re

from anthropic import Anthropic

logger = logging.getLogger("market_trends.talking_points")

MODEL = "claude-sonnet-5"

SYSTEM_PROMPT = """You write short, plain-English market talking points for real estate \
agents to say out loud to their clients in Orange County, CA. You will be given one \
city's current whole-market stats. Produce two short lists:

- "buyer": 3-4 bullets an agent could say to a prospective BUYER about this city's market \
  right now (e.g. negotiating leverage, inventory, pricing trends, timing).
- "seller": 3-4 bullets an agent could say to a prospective SELLER about this city's market \
  right now (e.g. pricing strategy, how fast homes are moving, demand).

Rules:
- Each bullet is one sentence under 30 words, conversational, no jargon, safe to \
repeat verbatim to a client.
- Never use percentages or percent signs. Describe movement in plain words instead \
  ("prices have been climbing since the spring", "homes are sitting a little longer than \
  they did a year ago"). Whole dollar figures and counts are fine.
- Ground every bullet in the figures given. Never invent a number that wasn't provided.
- Do not give legal, tax, or financial advice, and don't guarantee future price movement.
- Respond with ONLY one valid JSON object containing both lists, and nothing else: \
{"buyer": ["...", "..."], "seller": ["...", "..."]}
"""

# Which absolute figures are worth spending input tokens on. The percent-change
# columns are deliberately absent — the prompt forbids quoting percentages, so
# sending them is paid-for context the model isn't allowed to use. Their
# direction is passed instead, as a word (see _DIRECTION_FIELDS).
_ABSOLUTE_FIELDS = (
    ("median_sold_price", "median sold price (last 30 days)", 0),
    ("median_list_price", "median asking price of homes for sale", 0),
    ("median_price_per_sqft", "median price per square foot", 0),
    ("median_dom", "median days on market", 0),
    ("active_inventory", "homes for sale right now", 0),
    ("new_listings_7d", "new listings in the last week", 0),
    ("pending_count", "homes under contract", 0),
    ("homes_sold_30d", "homes sold in the last 30 days", 0),
    # The only one where the decimal carries meaning — 2.4 months and 2.9
    # months are different markets, and both round to "2".
    ("months_of_supply", "months of supply", 1),
)

# Percent-change columns, restated as a direction word. Each carries the pair
# of words that reads naturally for that particular metric — "days on market:
# higher" is technically right but nobody says it that way.
_DIRECTION_FIELDS = (
    ("price_change_vs_90d", "sold prices vs. three months ago", "higher", "lower"),
    ("price_change_yoy", "sold prices vs. a year ago", "higher", "lower"),
    ("inventory_change_yoy", "homes for sale vs. a year ago", "more", "fewer"),
    ("homes_sold_change_yoy", "homes selling vs. a year ago", "more", "fewer"),
    ("dom_change_yoy", "time it takes a home to sell vs. a year ago", "longer", "shorter"),
)

# Below this, a move is noise rather than a trend worth an agent repeating.
_FLAT_THRESHOLD_PCT = 2.0


def _direction(pct: float | None, up_word: str = "higher", down_word: str = "lower") -> str | None:
    if pct is None:
        return None
    if abs(pct) < _FLAT_THRESHOLD_PCT:
        return "about the same"
    return up_word if pct > 0 else down_word


def _offer_strength(ratio: float | None) -> str | None:
    """sold_to_list_ratio is itself a percentage, so it gets translated too."""
    if ratio is None:
        return None
    if ratio >= 100.5:
        return "homes are typically selling above asking price"
    if ratio >= 99:
        return "homes are typically selling right around asking price"
    return "homes are typically selling below asking price"


def _format_stats(stats: dict) -> str:
    """Compact, percent-free view of one city's stats.

    Sending the raw stats dict cost ~2x the input tokens and included every
    null column and every percent change, none of which can appear in the
    output under the rules above.
    """
    lines = []
    for key, label, decimals in _ABSOLUTE_FIELDS:
        value = stats.get(key)
        if value is None:
            continue
        rounded = round(float(value), decimals) if decimals else round(float(value))
        lines.append(f"- {label}: {rounded}")

    for key, label, up_word, down_word in _DIRECTION_FIELDS:
        direction = _direction(stats.get(key), up_word, down_word)
        if direction is None:
            continue
        lines.append(f"- {label}: {direction}")

    offers = _offer_strength(stats.get("sold_to_list_ratio"))
    if offers:
        lines.append(f"- {offers}")

    return "\n".join(lines)


def _extract_json(text: str) -> dict:
    """Pulls the talking-point object out of a model response.

    Has to tolerate three things seen in real runs: a bare JSON object, an
    object wrapped in a ```json ... ``` fence, and the response arriving as
    two separate objects ({"buyer": ...} then {"seller": ...}) rather than
    one. Scanning with raw_decode and merging handles all three; the earlier
    greedy `\\{.*\\}` regex broke on the last one, matching from the first
    brace to the last and then failing with "Extra data".
    """
    decoder = json.JSONDecoder()
    merged: dict = {}
    index = 0
    while True:
        start = text.find("{", index)
        if start == -1:
            break
        try:
            obj, end = decoder.raw_decode(text, start)
        except ValueError:
            # Not the start of a valid object (a stray brace in prose, say).
            index = start + 1
            continue
        if isinstance(obj, dict):
            for key, value in obj.items():
                merged.setdefault(key, value)
        index = end

    if not merged:
        raise ValueError(
            "no complete JSON object in response (truncated?): " f"{text[:200]!r}"
        )
    return merged


def generate_talking_points(city_name: str, stats: dict) -> dict[str, list[str]] | None:
    """One API call per city per run — whole-market (all property types) only.

    Results are stored in the talking_points table; the dashboard reads the
    stored rows, so no API call happens on a page view.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY not set, skipping talking point generation")
        return None

    client = Anthropic(api_key=api_key)

    stat_lines = _format_stats(stats)
    if not stat_lines:
        logger.warning("no usable stats for %s, skipping talking points", city_name)
        return None

    user_prompt = f"City: {city_name}, Orange County, CA\n\n{stat_lines}"

    try:
        response = client.messages.create(
            model=MODEL,
            # Billing is on tokens actually generated, not on this cap, so a
            # generous ceiling costs nothing and a tight one just truncates
            # the JSON mid-string. 700 was too tight for wordier cities
            # (Dana Point, Villa Park) and lost their points entirely.
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        if response.stop_reason == "max_tokens":
            # Say so plainly — otherwise this surfaces downstream as a
            # confusing "no JSON object found" parse error.
            logger.warning(
                "response for %s hit the max_tokens ceiling and was truncated", city_name
            )
        text = "".join(block.text for block in response.content if block.type == "text")
        parsed = _extract_json(text)
        buyer = [str(p) for p in parsed.get("buyer", [])]
        seller = [str(p) for p in parsed.get("seller", [])]
        return {"buyer": buyer, "seller": seller}
    except Exception:  # noqa: BLE001 - one city's failure shouldn't kill the run
        logger.exception("talking point generation failed for %s", city_name)
        return None
