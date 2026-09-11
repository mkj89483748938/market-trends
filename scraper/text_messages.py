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

from talking_points import MODEL, _extract_json, _format_stats

logger = logging.getLogger("market_trends.text_messages")

# SMS splits into multiple segments past 160 characters, and a wall of text
# from an agent reads like a mass blast. Kept tight and enforced in the
# prompt; over-long ones are flagged in the logs rather than silently sent.
MAX_MESSAGE_CHARS = 320

SYSTEM_PROMPT = """You write short follow-up text messages that a real estate agent \
in Orange County, CA sends to a lead they have already spoken with. You will be given \
one city's current market numbers. Produce two lists:

- "buyer": 3 messages to a prospective BUYER lead who has gone quiet.
- "seller": 3 messages to a prospective SELLER lead who has gone quiet.

Rules:
- Each message is a complete text, ready to send with no editing, under 300 characters.
- Write like a person texting, not like marketing copy. No emoji, no ALL CAPS, no \
exclamation-heavy hype, no "Just checking in!" openers.
- Use {first_name} exactly once at the start as a placeholder for the lead's name.
- Give the text a reason to exist: one specific, current fact about their city's market \
from the numbers provided, in plain words.
- Never use percentages or percent signs. Whole dollar figures and counts are fine.
- Never invent a number that wasn't provided.
- End with one short, easy question that invites a reply.
- No legal, tax, or financial advice. Never guarantee future prices or promise a result.
- Don't claim the lead did something they may not have done (no "since you toured...").
- Respond with ONLY one valid JSON object containing both lists, and nothing else: \
{"buyer": ["...", "..."], "seller": ["...", "..."]}
"""


def generate_text_messages(city_name: str, stats: dict) -> dict[str, list[str]] | None:
    """One API call per city per run. Results are stored, so the dashboard
    never calls the API on a page view."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY not set, skipping text message generation")
        return None

    stat_lines = _format_stats(stats)
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
        return result
    except Exception:  # noqa: BLE001 - one city's failure shouldn't kill the run
        logger.exception("text message generation failed for %s", city_name)
        return None
