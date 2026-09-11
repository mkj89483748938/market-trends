"""Suggested follow-up texts an agent can send a lead.

Separate from talking_points on purpose. Talking points are lines to say on
a call; these are messages short enough to send as written, which makes them
a different writing problem: they need a reason for arriving, one question,
and a length that doesn't get split into three SMS segments.

Reuses the same percent-free, absolute-figures payload as the talking
points, so both features describe the market the same way.
"""

import logging
import os

from anthropic import Anthropic

from talking_points import MODEL, _direction, _extract_json, _offer_strength

logger = logging.getLogger("market_trends.text_messages")

# SMS splits into multiple segments past 160 characters, and a wall of text
# from an agent reads like a mass blast. Kept tight and enforced in the
# prompt; over-long ones are flagged in the logs rather than silently sent.
MAX_MESSAGE_CHARS = 320

# Season names are a specific failure seen in review: told "prices are lower
# than three months ago", the model wrote "prices have eased since the
# spring" — but three months before September is June. The prompt forbids it;
# this catches it in the logs if it recurs, since the drift is plausible
# enough to read right.
_SEASON_WORDS = ("spring", "summer", "autumn", "fall", "winter")

SYSTEM_PROMPT = """You write short follow-up text messages that a real estate agent \
in Orange County, CA sends to a lead they have already spoken with but who has gone \
quiet. Produce two lists:

- "buyer": 3 messages to a prospective BUYER lead.
- "seller": 3 messages to a prospective SELLER lead.

What these texts are for: moving someone off the fence. The lead is interested but \
stalled, and the job is to give them a real reason this moment is worth acting on, \
explained clearly enough that they learn something about their market. Teach, then \
invite — the market facts are what make it persuasive, so lead with what's genuinely \
happening and let that do the work.

Numbers:
- You MAY quote the counts of homes given below (homes for sale, new listings, homes \
under contract, homes sold). Those are concrete and easy to picture.
- You must NOT state any price, dollar amount, or number of days. Describe prices and \
how fast homes are selling in words only, using the trends given \
("prices have come down a little since three months ago", "homes are sitting a bit \
longer than they were last year"). No percentages or percent signs anywhere.
- Never invent a number, trend, or fact that wasn't provided.
- Say the timeframe exactly as it is given to you. If a trend is described as three \
months ago, call it three months ago. Never substitute a season name or any other \
period for the timeframe you were given.
- Only make a comparison if a trend line below actually provides it. If you are not \
told how something compares with last year or last quarter, do not imply it. In \
particular, a count of homes for sale on its own does NOT tell you whether there is \
more or less to choose from than before — describe it as what is available now.

Style:
- Each message is a complete text, ready to send with no editing, under 300 characters.
- Write like a person texting, not marketing copy. No emoji, no ALL CAPS, no \
"Just checking in!" openers, no more than one exclamation mark across all six messages.
- Use {first_name} exactly once at the start as a placeholder for the lead's name.
- End with one short, easy question that invites a reply.

Lines not to cross:
- Build urgency only from the market facts you were given. No invented deadlines, no \
"this window is closing", no fear of missing out, no pressure.
- Never predict or guarantee where prices, rates, or the market are heading.
- No legal, tax, or financial advice.
- Don't claim the lead did something they may not have done (no "since you toured...").

Respond with ONLY one valid JSON object containing both lists, and nothing else: \
{"buyer": ["...", "..."], "seller": ["...", "..."]}
"""

# Counts the messages are allowed to quote: whole homes, easy to picture, and
# nothing a client could dispute.
_QUOTABLE_COUNTS = (
    ("active_inventory", "homes for sale right now"),
    ("new_listings_7d", "new listings this week"),
    ("pending_count", "homes currently under contract"),
    ("homes_sold_30d", "homes sold in the last 30 days"),
)

# Prices and days-on-market reach the model as direction words only. The
# figures themselves are deliberately never sent: the prompt forbids quoting
# them, so including them would be paid-for context the model can't use and a
# number it might leak anyway.
_TREND_FIELDS = (
    ("price_change_vs_90d", "prices compared with three months ago", "higher", "lower"),
    ("price_change_yoy", "prices compared with a year ago", "higher", "lower"),
    ("inventory_change_yoy", "homes to choose from compared with a year ago", "more", "fewer"),
    ("dom_change_yoy", "how long homes take to sell compared with a year ago", "longer", "shorter"),
)


def _market_balance(months_of_supply: float | None) -> str | None:
    """Months of supply as a plain-English market description.

    The industry rule of thumb: under ~3 months favours sellers, over ~6
    favours buyers. Sent as words so the model has the market's character
    without a figure it would be tempted to quote.
    """
    if months_of_supply is None:
        return None
    if months_of_supply < 3:
        return "homes are getting picked up quickly and sellers have the advantage"
    if months_of_supply > 6:
        return "homes are taking a while to sell and buyers have room to negotiate"
    return "supply and demand are fairly balanced right now"


def _format_sms_stats(stats: dict) -> str:
    """Percent-free, price-free payload for the follow-up texts.

    Separate from the talking points' payload because the rules differ: the
    talking points may cite a median price, these may not.
    """
    counts = []
    for key, label in _QUOTABLE_COUNTS:
        value = stats.get(key)
        if value is not None:
            counts.append(f"- {label}: {round(float(value))}")

    trends = []
    for key, label, up_word, down_word in _TREND_FIELDS:
        direction = _direction(stats.get(key), up_word, down_word)
        if direction is not None:
            trends.append(f"- {label}: {direction}")

    balance = _market_balance(stats.get("months_of_supply"))
    if balance:
        trends.append(f"- {balance}")

    offers = _offer_strength(stats.get("sold_to_list_ratio"))
    if offers:
        trends.append(f"- {offers}")

    sections = []
    if counts:
        sections.append("Counts you may quote:\n" + "\n".join(counts))
    if trends:
        sections.append(
            "Trends — describe these in words, never as a figure:\n" + "\n".join(trends)
        )
    return "\n\n".join(sections)


def generate_text_messages(city_name: str, stats: dict) -> dict[str, list[str]] | None:
    """One API call per city per run. Results are stored, so the dashboard
    never calls the API on a page view."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY not set, skipping text message generation")
        return None

    stat_lines = _format_sms_stats(stats)
    if not stat_lines:
        logger.warning("no usable stats for %s, skipping text messages", city_name)
        return None

    client = Anthropic(api_key=api_key)
    user_prompt = f"City: {city_name}, Orange County, CA\n\n{stat_lines}"

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        if response.stop_reason == "max_tokens":
            logger.warning("text messages for %s were truncated at max_tokens", city_name)

        text = "".join(block.text for block in response.content if block.type == "text")
        parsed = _extract_json(text)
        result = {
            "buyer": [str(m).strip() for m in parsed.get("buyer", [])],
            "seller": [str(m).strip() for m in parsed.get("seller", [])],
        }

        for audience, messages in result.items():
            for message in messages:
                if len(message) > MAX_MESSAGE_CHARS:
                    logger.warning(
                        "%s %s message is %d chars (over %d) — may split across texts",
                        city_name,
                        audience,
                        len(message),
                        MAX_MESSAGE_CHARS,
                    )
                lowered = message.lower()
                season = next((w for w in _SEASON_WORDS if w in lowered), None)
                if season:
                    logger.warning(
                        "%s %s message says %r — check the timeframe is right: %s",
                        city_name,
                        audience,
                        season,
                        message,
                    )
        return result
    except Exception:  # noqa: BLE001 - one city's failure shouldn't kill the run
        logger.exception("text message generation failed for %s", city_name)
        return None
