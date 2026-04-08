"""
Caption Renderer — Module 5

Transcribes narration.mp3 using whisper-timestamped to get word-level timestamps,
groups words into chunks of ≤5 words, and writes captions.json.

Public API:
    run(narration_mp3_path: Path, output_dir: Path) -> list[dict]
    Returns: [{text: str, start: float, end: float}, ...]

Environment:
    (no API keys required — whisper runs locally)
"""

from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path
from typing import Any

try:
    import whisper_timestamped
except ImportError:
    import types as _types

    whisper_timestamped = _types.SimpleNamespace()  # patched entirely by tests

logger = logging.getLogger(__name__)

_MAX_WORDS_PER_CHUNK = 5


def get_audio_duration(path: Path) -> float:
    """Return audio duration in seconds using ffprobe."""
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(result.stdout.strip())


def _extract_words(whisper_result: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten whisper-timestamped result into a list of word dicts."""
    words: list[dict[str, Any]] = []
    for segment in whisper_result.get("segments", []):
        for w in segment.get("words", []):
            words.append(
                {
                    "word": w["word"].strip(),
                    "start": float(w["start"]),
                    "end": float(w["end"]),
                }
            )
    return words


def _group_into_chunks(
    words: list[dict[str, Any]],
    max_words: int,
    audio_duration: float,
) -> list[dict[str, Any]]:
    """Group words into caption chunks of at most max_words."""
    chunks: list[dict[str, Any]] = []
    i = 0
    while i < len(words):
        batch = words[i : i + max_words]
        text = " ".join(w["word"] for w in batch)
        start = batch[0]["start"]
        end = min(batch[-1]["end"], audio_duration)

        # Ensure start < end
        if start >= end:
            end = min(start + 0.1, audio_duration)

        chunks.append({"text": text, "start": start, "end": end})
        i += max_words

    # Ensure non-overlapping: clip each chunk's end to the next chunk's start
    for j in range(len(chunks) - 1):
        if chunks[j]["end"] > chunks[j + 1]["start"]:
            chunks[j]["end"] = chunks[j + 1]["start"]

    return chunks


def run(
    narration_mp3_path: Path,
    output_dir: Path,
    model_size: str = "tiny",
    max_words_per_chunk: int = _MAX_WORDS_PER_CHUNK,
) -> list[dict[str, Any]]:
    """
    Transcribe narration audio and produce word-level caption chunks.

    Args:
        narration_mp3_path: Path to the narration.mp3 file
        output_dir:          Directory where captions.json will be written
        model_size:          Whisper model size (tiny/base/small/medium/large)
        max_words_per_chunk: Maximum words per caption chunk

    Returns:
        List of caption dicts: [{text: str, start: float, end: float}, ...]
    """
    audio_duration = get_audio_duration(narration_mp3_path)
    logger.info("Transcribing audio (%.1fs) with whisper-%s", audio_duration, model_size)

    model = whisper_timestamped.load_model(model_size)
    result = whisper_timestamped.transcribe(model, str(narration_mp3_path))

    words = _extract_words(result)
    logger.info("Extracted %d words from transcription", len(words))

    chunks = _group_into_chunks(words, max_words_per_chunk, audio_duration)
    logger.info("Grouped into %d caption chunks", len(chunks))

    captions_path = output_dir / "captions.json"
    captions_path.write_text(json.dumps(chunks, indent=2))

    return chunks
