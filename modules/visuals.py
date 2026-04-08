"""
Visual Generator — Module 4

For each research item, uses Claude to write a cinematic image prompt,
then generates a 1280×720 image via Replicate (Flux.1-schnell) and downloads it.

Public API:
    run(research_items, output_dir, replicate_client, claude_client) -> list[str]
    Returns a list of 10 absolute file path strings: output_dir/images/item_1.png…item_10.png

Environment:
    ANTHROPIC_API_KEY
    REPLICATE_API_TOKEN
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Any

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

_REPLICATE_MODEL = "black-forest-labs/flux-schnell"

_PROMPT_SYSTEM = """\
You are a creative director for YouTube thumbnails and video visuals.
Write a single, vivid image generation prompt (≤30 words) for a given subject.
The image must be: dramatic, cinematic, 16:9 composition, high detail, no text.
Return ONLY the prompt text. No quotes, no explanation.
"""


def _make_clients():
    import anthropic
    import replicate

    claude = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    rep = replicate.Client(api_token=os.environ["REPLICATE_API_TOKEN"])
    return claude, rep


def _generate_image_prompt(claude_client: Any, item: dict[str, Any]) -> str:
    """Use Claude to generate a cinematic image prompt for a research item."""
    message = claude_client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=128,
        system=_PROMPT_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Subject: {item['title']}\n"
                    f"Facts: {item.get('facts', '')}\n"
                    "Write a dramatic, cinematic image prompt."
                ),
            }
        ],
    )
    return message.content[0].text.strip()


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=30))
def _generate_and_save_image(
    replicate_client: Any,
    prompt: str,
    out_path: Path,
    width: int = 1280,
    height: int = 720,
) -> Path:
    """Call Replicate to generate an image and save it to out_path."""
    if out_path.exists():
        logger.debug("Skipping existing image: %s", out_path.name)
        return out_path

    result = replicate_client.run(
        _REPLICATE_MODEL,
        input={
            "prompt": prompt,
            "width": width,
            "height": height,
            "num_outputs": 1,
        },
    )

    image_url = result[0] if isinstance(result, list) else result

    response = requests.get(str(image_url), timeout=30)
    response.raise_for_status()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(response.content)

    size = out_path.stat().st_size
    if size < 512:
        out_path.unlink()
        raise ValueError(f"Generated image too small ({size}B) — likely blank")

    return out_path


def _process_item(
    item: dict[str, Any],
    images_dir: Path,
    replicate_client: Any,
    claude_client: Any,
    width: int,
    height: int,
) -> str:
    """Generate a single image for one research item. Runs in a thread worker."""
    rank = int(item["rank"])
    out_path = images_dir / f"item_{rank}.png"

    logger.info("Generating image for rank %d: %s", rank, item["title"])
    prompt = _generate_image_prompt(claude_client, item)
    logger.debug("Image prompt for rank %d: %s", rank, prompt)

    _generate_and_save_image(replicate_client, prompt, out_path, width, height)
    return str(out_path)


async def _run_concurrent(
    research_items: list[dict[str, Any]],
    images_dir: Path,
    replicate_client: Any,
    claude_client: Any,
    width: int,
    height: int,
    max_concurrent: int,
) -> list[str]:
    """Run image generation for all items with bounded concurrency."""
    loop = asyncio.get_event_loop()
    semaphore = asyncio.Semaphore(max_concurrent)

    async def bounded_process(item: dict[str, Any]) -> str:
        async with semaphore:
            return await loop.run_in_executor(
                None,  # uses default ThreadPoolExecutor
                _process_item,
                item,
                images_dir,
                replicate_client,
                claude_client,
                width,
                height,
            )

    tasks = [bounded_process(item) for item in research_items]
    return await asyncio.gather(*tasks)


def run(
    research_items: list[dict[str, Any]],
    output_dir: Path,
    replicate_client: Any = None,
    claude_client: Any = None,
    width: int = 1280,
    height: int = 720,
    max_concurrent: int = 5,
) -> list[str]:
    """
    Generate images for all 10 research items in parallel (up to max_concurrent).

    Args:
        research_items:   10 dicts from research.run(), sorted rank 10→1
        output_dir:       Root output directory for this pipeline run
        replicate_client: Replicate client (created from env if None)
        claude_client:    Anthropic client (created from env if None)
        width, height:    Output image dimensions (default 1280×720)
        max_concurrent:   Max simultaneous Replicate requests (default 5)

    Returns:
        List of 10 absolute path strings for the generated images.
        Files are at output_dir/images/item_{rank}.png, sorted by rank.
    """
    if replicate_client is None or claude_client is None:
        _claude, _rep = _make_clients()
        if claude_client is None:
            claude_client = _claude
        if replicate_client is None:
            replicate_client = _rep

    images_dir = output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    paths: list[str] = asyncio.run(
        _run_concurrent(
            research_items,
            images_dir,
            replicate_client,
            claude_client,
            width,
            height,
            max_concurrent,
        )
    )

    paths.sort(key=lambda p: int(Path(p).stem.split("_")[1]))
    logger.info("Generated %d images in %s", len(paths), images_dir)
    return paths
