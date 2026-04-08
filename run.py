#!/usr/bin/env python3
"""
Top 10 YouTube Video Generator — CLI Entry Point

Usage:
    python run.py --topic "Top 10 Dangerous Animals"
    python run.py --topic "Top 10 Fastest Cars" --output-dir ./output
    python run.py --topic "Top 10 Deepest Oceans" --no-resume
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )
    # Suppress noisy third-party loggers
    for noisy in ("httpx", "httpcore", "urllib3", "PIL"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def _load_config(config_path: str) -> dict:
    with open(config_path) as f:
        cfg = yaml.safe_load(f)
    return cfg


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a Top 10 YouTube video from a topic.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--topic",
        required=True,
        help='The countdown topic, e.g. "Top 10 Dangerous Animals"',
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Root directory for all generated artifacts (default: output/)",
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to config.yaml (default: config.yaml)",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Ignore existing checkpoint and restart from scratch",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()
    _configure_logging(args.verbose)

    logger = logging.getLogger(__name__)

    config = _load_config(args.config)

    if args.no_resume:
        config.setdefault("pipeline", {})["resume_on_crash"] = False

    from pipeline import Pipeline

    slug = args.topic.lower().replace(" ", "_")
    output_dir = Path(args.output_dir) / slug

    if args.no_resume and output_dir.exists():
        import shutil

        shutil.rmtree(output_dir)

    logger.info("Starting pipeline for topic: %s", args.topic)
    p = Pipeline(args.topic, output_dir)
    try:
        p.run()
        final_video = output_dir / "final_video.mp4"
        print(f"\nDone! Final video: {final_video}")
    except Exception as e:
        logger.error("Pipeline failed: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
