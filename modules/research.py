"""
Research Engine — Module 1

Uses Tavily to search the web for a given topic and Claude to rank/structure
the results into exactly 10 items with facts and a hook line per item.

Public API:
    run(topic: str) -> list[dict]
    Each dict: {rank, title, facts, hook_line}

Environment:
    ANTHROPIC_API_KEY
    TAVILY_API_KEY
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

import anthropic

try:
    from tavily import TavilyClient
except ImportError:
    import types as _types

    TavilyClient = _types.SimpleNamespace  # patched entirely by tests
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


def tavily_search(
    query: str,
    depth: str = "advanced",
    max_results: int = 10,
) -> list[dict[str, Any]]:
    """Module-level wrapper around TavilyClient.search for testability."""
    client = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY", ""))
    response = client.search(query=query, search_depth=depth, max_results=max_results)
    return response.get("results", [])


_RANKING_SYSTEM = """\
You are a research assistant for a Top 10 YouTube countdown video.
Given web search results about a topic, extract and rank exactly 10 items.

Rules:
- Return ONLY valid JSON — no markdown fences, no commentary.
- The list must contain exactly 10 objects in countdown order (rank 10 = least extreme, rank 1 = most extreme/surprising).
- Each object must have these keys:
    "rank"      : integer 1–10
    "title"     : short name/label for this item (≤8 words)
    "facts"     : list of 3–5 concise factual bullets about the item
    "hook_line" : one punchy sentence that would make a viewer lean forward (≤20 words)
- Avoid duplicates. Prefer items that are verifiable and compelling.
- Do NOT include any text outside the JSON array.
"""

_RANKING_USER_TMPL = """\
Topic: {topic}

Web search results:
{search_text}

Return a JSON array of exactly 10 ranked items.
"""


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _rank_with_claude(topic: str, search_text: str, model: str) -> list[dict[str, Any]]:
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
    prompt = _RANKING_USER_TMPL.format(topic=topic, search_text=search_text)

    message = client.messages.create(
        model=model,
        max_tokens=2048,
        system=_RANKING_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = message.content[0].text.strip()

    # Strip accidental markdown fences: ```json ... ``` or ``` ... ```
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    raw = raw.strip()

    items: list[dict[str, Any]] = json.loads(raw)

    if len(items) != 10:
        raise ValueError(f"Expected 10 items, got {len(items)}")

    # Normalise: ensure rank is int, sort descending (10 → 1)
    for item in items:
        item["rank"] = int(item["rank"])
    items.sort(key=lambda x: x["rank"], reverse=True)

    return items


def run(
    topic: str,
    model: str = "claude-3-5-sonnet-20241022",
    search_depth: str = "advanced",
    search_max_results: int = 10,
) -> list[dict[str, Any]]:
    """
    Research a topic and return a ranked list of exactly 10 items.

    Args:
        topic: The countdown topic, e.g. "Top 10 Dangerous Animals"
        model: Anthropic model ID
        search_depth: Tavily search depth ("basic" or "advanced")
        search_max_results: Max results per Tavily query

    Returns:
        List of 10 dicts: [{rank, title, facts, hook_line}, ...]
        Sorted rank 10 → 1 (least extreme first).
    """
    logger.info("Researching topic: %s", topic)

    results = tavily_search(
        query=f"top 10 {topic}",
        depth=search_depth,
        max_results=search_max_results,
    )

    lines: list[str] = []
    for i, r in enumerate(results, 1):
        title = r.get("title", "")
        content = r.get("content", "")
        lines.append(f"[{i}] {title}\n{content[:400]}")
    search_text = "\n\n".join(lines)

    items = _rank_with_claude(topic, search_text, model)
    logger.info("Ranked %d items for topic '%s'", len(items), topic)
    return items
