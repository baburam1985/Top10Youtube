"""
Script Generator — Module 2

Takes ranked research items and uses Claude to write a full narration script
structured as segments:
  - Intro hook (index 0)
  - Items 10 → 1 (indices 1–10, each ~40 words)
  - CTA outro (index 11)

Public API:
    run(research_items: list[dict]) -> dict
    Returns: {full_script: str, segments: [{index: int, text: str, label: str}]}

Environment:
    ANTHROPIC_API_KEY
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


_SCRIPT_SYSTEM = """\
You are a YouTube scriptwriter for Top 10 countdown videos.
Write an engaging, conversational narration script — no stage directions, just spoken words.

Rules:
- Return ONLY valid JSON — no markdown fences, no commentary.
- The JSON must have a single key "segments": an array of objects, each with:
    "index" : integer (0=intro, 1=item rank-10, 2=item rank-9, ..., 10=item rank-1, 11=outro)
    "label" : short label (e.g. "Intro", "Number 10: <title>", "Outro")
    "text"  : the narration text for this segment
- Target lengths:
    Intro (index 0): ~35 words — tease the topic, build suspense
    Each item (index 1–10): ~40 words — hook, fact, transition to next
    Outro (index 11): ~25 words — subscribe CTA, tease next video
- Tone: dramatic, enthusiastic, slightly educational
- Do NOT write item titles as headings — weave them into narration.
- Do NOT include any text outside the JSON object.
"""

_SCRIPT_USER_TMPL = """\
Topic: {topic}

Ranked research items (10 = least extreme → 1 = most extreme):
{items_json}

Write the full narration script as a JSON object with a "segments" key.
"""


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _generate_with_claude(
    research_items: list[dict[str, Any]],
    model: str,
    words_per_segment: int,
) -> dict[str, Any]:
    # Infer topic from items if not provided
    topic = "Top 10 countdown"

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
    user_prompt = _SCRIPT_USER_TMPL.format(
        topic=topic,
        items_json=json.dumps(research_items, indent=2),
    )

    message = client.messages.create(
        model=model,
        max_tokens=4096,
        system=_SCRIPT_SYSTEM,
        messages=[{"role": "user", "content": user_prompt}],
    )
    raw = message.content[0].text.strip()

    # Strip accidental markdown fences: ```json ... ``` or ``` ... ```
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    raw = raw.strip()

    data = json.loads(raw)
    segments = data["segments"]

    if len(segments) != 12:
        raise ValueError(f"Expected 12 segments (intro + 10 + outro), got {len(segments)}")

    # Normalise — ensure required keys exist
    for seg in segments:
        seg["index"] = int(seg["index"])
        seg.setdefault("label", f"Segment {seg['index']}")

    segments.sort(key=lambda s: s["index"])

    # Word-count guard
    for seg in segments[1:11]:
        word_count = len(seg["text"].split())
        if word_count > words_per_segment * 2:
            logger.warning(
                "Segment %d has %d words — may produce too-long video",
                seg["index"],
                word_count,
            )

    full_script = "\n\n".join(s["text"] for s in segments)
    return {"full_script": full_script, "segments": segments}


def run(
    research_items: list[dict[str, Any]],
    topic: str = "Top 10 countdown",
    model: str = "claude-3-5-sonnet-20241022",
    words_per_segment: int = 40,
) -> dict[str, Any]:
    """
    Generate a narration script from ranked research items.

    Args:
        research_items: List of 10 dicts from research.run()
        topic:          Countdown topic string (used in prompt)
        model:          Anthropic model ID
        words_per_segment: Target word count per item segment

    Returns:
        {
            "full_script": str,
            "segments": [{"index": int, "label": str, "text": str}, ...]
        }
    """
    logger.info("Generating script for %d research items", len(research_items))
    result = _generate_with_claude(research_items, model, words_per_segment)
    total_words = sum(len(s["text"].split()) for s in result["segments"])
    logger.info(
        "Script generated: %d segments, ~%d words (~%.0fs)",
        len(result["segments"]),
        total_words,
        total_words / 2.5,
    )
    return result
