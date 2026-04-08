"""YouTube metadata generation module."""

import json
from pathlib import Path


def run(topic, script, output_dir):
    """
    Generate YouTube upload metadata (title, description, tags).

    Args:
        topic:      Countdown topic string.
        script:     Script dict with full_script and segments.
        output_dir: Directory where metadata.json is written.

    Returns:
        dict with title, description, tags.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    meta = {
        "title": f"{topic} - Top 10 Countdown",
        "description": (
            f"Watch our epic countdown of {topic}! "
            "From the surprising to the shocking — you won't believe number 1!"
        ),
        "tags": ["top10", "countdown", topic.lower().replace(" ", ""), "viral", "facts"],
    }

    meta_path = output_dir / "metadata.json"
    meta_path.write_text(json.dumps(meta, indent=2))
    return meta
