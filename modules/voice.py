"""
Voice Synthesis — Module 3

Synthesizes each script segment to audio using ElevenLabs, concatenates
them via ffmpeg into a single narration.mp3, and writes segment_timestamps.json.

Public API:
    run(segments, output_dir, client=None) -> None

Output files (in output_dir):
    segments/segment_NN.mp3      — one file per segment
    narration.mp3                — concatenated full narration
    segment_timestamps.json      — {index: start_seconds, ...}

Environment:
    ELEVENLABS_API_KEY
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential


@dataclass
class SegmentTimestamp:
    """Timing metadata for a synthesized segment. Used by assembler."""

    index: int
    label: str
    start_ms: int
    end_ms: int
    audio_file: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


logger = logging.getLogger(__name__)

_DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"
_DEFAULT_MODEL_ID = "eleven_turbo_v2_5"


def _make_elevenlabs_client():
    from elevenlabs.client import ElevenLabs

    return ElevenLabs(api_key=os.environ["ELEVENLABS_API_KEY"])


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=15))
def _synthesize_segment(
    client: Any,
    text: str,
    out_path: Path,
    voice_id: str = _DEFAULT_VOICE_ID,
    model_id: str = _DEFAULT_MODEL_ID,
    stability: float = 0.5,
    similarity_boost: float = 0.75,
) -> None:
    """Write synthesized audio for `text` to `out_path`."""
    if out_path.exists():
        logger.debug("Skipping already-synthesized: %s", out_path.name)
        return

    audio = client.generate(
        text=text,
        voice=voice_id,
        model=model_id,
        voice_settings={
            "stability": stability,
            "similarity_boost": similarity_boost,
        },
    )

    with open(out_path, "wb") as f:
        for chunk in audio:
            f.write(chunk)


def _get_audio_duration_s(path: Path) -> float:
    """Return audio duration in seconds using ffprobe. Returns 0.0 on failure."""
    try:
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
    except Exception:
        return 0.0


def _concatenate_segments(segment_paths: list[Path], output_path: Path) -> None:
    """Concatenate segment mp3 files into a single mp3 using ffmpeg."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        for p in segment_paths:
            # ffmpeg concat format: escape single quotes by ending the quote, escaping, reopening
            safe_path = str(p.resolve()).replace("'", "'\\''")
            f.write(f"file '{safe_path}'\n")
        concat_list = f.name

    try:
        output_path.touch()
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                concat_list,
                "-c",
                "copy",
                str(output_path),
            ],
            check=True,
            capture_output=True,
        )
    finally:
        os.unlink(concat_list)


def run(
    segments: list[dict[str, Any]],
    output_dir: Path,
    client: Any = None,
    voice_id: str = _DEFAULT_VOICE_ID,
    model_id: str = _DEFAULT_MODEL_ID,
    stability: float = 0.5,
    similarity_boost: float = 0.75,
) -> None:
    """
    Synthesize all script segments and write narration.mp3 + timestamps.

    Args:
        segments:    List of segment dicts with at minimum {"index": int, "text": str}
        output_dir:  Root output directory for this pipeline run
        client:      ElevenLabs client instance (created if None)
        voice_id:    ElevenLabs voice ID
        model_id:    ElevenLabs model ID
        stability:   Voice stability (0–1)
        similarity_boost: Voice similarity boost (0–1)
    """
    if client is None:
        client = _make_elevenlabs_client()

    segments_dir = output_dir / "segments"
    segments_dir.mkdir(parents=True, exist_ok=True)

    segment_paths: list[tuple[dict, Path]] = []
    for seg in segments:
        idx = int(seg["index"])
        out_path = segments_dir / f"segment_{idx:02d}.mp3"
        _synthesize_segment(
            client=client,
            text=seg["text"],
            out_path=out_path,
            voice_id=voice_id,
            model_id=model_id,
            stability=stability,
            similarity_boost=similarity_boost,
        )
        segment_paths.append((seg, out_path))

    if not segment_paths:
        raise RuntimeError("No segments were synthesized — cannot produce narration.mp3")

    narration_path = output_dir / "narration.mp3"
    _concatenate_segments([p for _, p in segment_paths], narration_path)

    # Build timestamps by accumulating durations
    timestamps: dict[str, float] = {}
    cursor_s = 0.0
    for seg, path in segment_paths:
        timestamps[str(seg["index"])] = cursor_s
        duration = _get_audio_duration_s(path)
        cursor_s += duration

    ts_path = output_dir / "segment_timestamps.json"
    ts_path.write_text(json.dumps(timestamps, indent=2))

    logger.info(
        "Voice synthesis complete. %d segments, ~%.1fs total narration",
        len(segment_paths),
        cursor_s,
    )
