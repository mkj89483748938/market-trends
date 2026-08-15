import json
import logging
import os
import re

from anthropic import Anthropic

logger = logging.getLogger("market_trends.talking_points")

MODEL = "claude-sonnet-5"

SYSTEM_PROMPT = """You write short, plain-English market talking points for real estate \
agents to say out loud to their clients in Orange County, CA. You will be given one \
city's current market stats. Produce two short lists:

- "buyer": 3-5 bullets an agent could say to a prospective BUYER about this city's market \
  right now (e.g. negotiating leverage, inventory, pricing trends, timing).
- "seller": 3-5 bullets an agent could say to a prospective SELLER about this city's market \
  right now (e.g. pricing strategy, how fast homes are moving, demand).

Rules:
- Each bullet is one sentence, conversational, no jargon, safe to repeat verbatim to a client.
- Ground every bullet in the numbers given. Never invent a statistic that wasn't provided.
- If a stat is missing (null), don't reference it.
- Do not give legal, tax, or financial advice, and don't guarantee future price movement.
- Respond with ONLY valid JSON: {"buyer": ["...", "..."], "seller": ["...", "..."]}
"""


def _extract_json(text: str) -> dict:
    """Claude is told to respond with ONLY JSON, but sometimes wraps it in a
    ```json ... ``` fence anyway. Pull out the {...} block instead of
    assuming the whole response is bare JSON.
    """
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return json.loads(match.group(0) if match else text)


def generate_talking_points(city_name: str, stats: dict) -> dict[str, list[str]] | None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY not set, skipping talking point generation")
        return None

    client = Anthropic(api_key=api_key)

    stat_lines = "\n".join(
        f"- {key}: {value}" for key, value in stats.items() if key not in ("city_id", "run_date")
    )
    user_prompt = f"City: {city_name}, Orange County, CA\n\nCurrent stats:\n{stat_lines}"

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=1200,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        text = "".join(block.text for block in response.content if block.type == "text")
        parsed = _extract_json(text)
        buyer = [str(p) for p in parsed.get("buyer", [])]
        seller = [str(p) for p in parsed.get("seller", [])]
        return {"buyer": buyer, "seller": seller}
    except Exception:  # noqa: BLE001 - one city's failure shouldn't kill the run
        logger.exception("talking point generation failed for %s", city_name)
        return None
