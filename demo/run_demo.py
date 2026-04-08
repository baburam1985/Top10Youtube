#!/usr/bin/env python3
"""
Demo runner — Top 10 YouTube Video Generator

Runs the full pipeline with mocked external APIs (no API keys required).
Uses the bundled ffmpeg from imageio-ffmpeg to produce a real, playable MP4.

Produces real output artifacts in demo/output/<slug>/:
  - pipeline_state.json        (checkpoint at DONE)
  - segments/segment_NN.mp3    (real silent audio per segment)
  - narration.mp3              (real concatenated silent audio)
  - segment_timestamps.json
  - images/item_N.png          (10 PIL-generated placeholder images)
  - captions.json
  - music.mp3
  - final_video.mp4            (REAL playable video — images + silent audio)
  - thumbnail.jpg
  - metadata.json
  - demo_summary.json

Usage:
    cd Top10Youtube
    python demo/run_demo.py
    python demo/run_demo.py --topic "Top 10 Ocean Mysteries"
    python demo/run_demo.py --clean   # wipe demo/output first
"""
from __future__ import annotations

import argparse
import json
import logging
import shutil
import subprocess
import sys
import tempfile
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("demo")

# ---------------------------------------------------------------------------
# Bundled ffmpeg (no system ffmpeg required)
# ---------------------------------------------------------------------------


def _get_ffmpeg() -> str:
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        raise RuntimeError("imageio-ffmpeg not found. Install it: pip install imageio-ffmpeg")


# ---------------------------------------------------------------------------
# Demo data
# ---------------------------------------------------------------------------

DEMO_RESEARCH_ITEMS = [
    {
        "rank": 10,
        "title": "Box Jellyfish",
        "facts": ["Kills within minutes", "Nearly invisible", "Multiple eyes"],
        "hook_line": "This transparent killer is almost impossible to spot in the water.",
    },
    {
        "rank": 9,
        "title": "Cone Snail",
        "facts": ["Venom has no antidote", "Harpoon-like tooth", "Found in tropical reefs"],
        "hook_line": "A pretty shell hides one of the deadliest venoms on Earth.",
    },
    {
        "rank": 8,
        "title": "Inland Taipan",
        "facts": ["Most toxic snake venom", "One bite kills 100 adults", "Found in Australia"],
        "hook_line": "One drop of its venom could wipe out a small crowd.",
    },
    {
        "rank": 7,
        "title": "Saltwater Crocodile",
        "facts": ["Strongest bite force", "Up to 7m long", "Apex predator"],
        "hook_line": "The largest reptile alive and an ambush predator with no equal.",
    },
    {
        "rank": 6,
        "title": "African Elephant",
        "facts": ["3,000+ lbs", "Charges at 25 mph", "400+ deaths per year"],
        "hook_line": "The planet's largest land animal is also one of its deadliest.",
    },
    {
        "rank": 5,
        "title": "Hippopotamus",
        "facts": ["500+ deaths per year in Africa", "Can outrun humans", "Highly territorial"],
        "hook_line": "Africa's most dangerous animal isn't the lion — it's this one.",
    },
    {
        "rank": 4,
        "title": "Cape Buffalo",
        "facts": ['Called "The Black Death"', "Gore and trample attackers", "Herd mentality"],
        "hook_line": "Hunters fear it more than lions — and for very good reason.",
    },
    {
        "rank": 3,
        "title": "Estuarine Crocodile",
        "facts": ["750+ psi bite", "Death roll technique", "Ambushes from water"],
        "hook_line": "It hasn't changed in 200 million years because it doesn't need to.",
    },
    {
        "rank": 2,
        "title": "African Lion",
        "facts": ["250+ lb apex predator", "Can leap 36 feet", "200 attacks/year"],
        "hook_line": "The king of the jungle earns that title every single day.",
    },
    {
        "rank": 1,
        "title": "Mosquito",
        "facts": ["700,000+ deaths/year", "Transmits malaria, dengue", "Found on every continent"],
        "hook_line": "The deadliest creature on Earth is small enough to fit on your fingertip.",
    },
]

DEMO_SCRIPT_SEGMENTS = [
    {
        "index": 0,
        "label": "Intro",
        "text": "What makes an animal truly dangerous? Today we count down the Top 10 most dangerous animals on Earth. Some will surprise you — stay tuned for number one.",
    },
    {
        "index": 1,
        "label": "Number 10: Box Jellyfish",
        "text": "Kicking off our list is the Box Jellyfish. Nearly invisible in water and capable of killing within minutes, this silent drifter is a nightmare for swimmers.",
    },
    {
        "index": 2,
        "label": "Number 9: Cone Snail",
        "text": "At number nine, the Cone Snail. Its beautiful shell conceals a harpoon-like tooth that injects venom with no known antidote. Pick it up at your peril.",
    },
    {
        "index": 3,
        "label": "Number 8: Inland Taipan",
        "text": "Number eight: the Inland Taipan. Australia's most venomous snake can kill a hundred adults with a single bite. Thankfully, it rarely meets humans.",
    },
    {
        "index": 4,
        "label": "Number 7: Saltwater Croc",
        "text": "At seven, the Saltwater Crocodile — the largest reptile alive. Its ambush technique is perfected over 200 million years of evolution.",
    },
    {
        "index": 5,
        "label": "Number 6: African Elephant",
        "text": "Number six: the African Elephant. At three thousand pounds and charging at twenty-five miles per hour, this gentle giant becomes a terrifying force when threatened.",
    },
    {
        "index": 6,
        "label": "Number 5: Hippopotamus",
        "text": "Halfway through — the Hippo. Responsible for over five hundred deaths annually in Africa, it is the continent's most aggressive large animal.",
    },
    {
        "index": 7,
        "label": "Number 4: Cape Buffalo",
        "text": "Number four: the Cape Buffalo, nicknamed the Black Death. When wounded, it circles back and charges with lethal precision. Hunters fear it more than lions.",
    },
    {
        "index": 8,
        "label": "Number 3: Estuarine Crocodile",
        "text": "At three, crocs return. Their death roll is biomechanical genius, and they hold their breath for over an hour waiting for prey. Patience is their superpower.",
    },
    {
        "index": 9,
        "label": "Number 2: African Lion",
        "text": "Number two: the African Lion. Two hundred attacks on humans per year, a forty-kilogram bite force, and a leap that covers thirty-six feet. The king earns its crown.",
    },
    {
        "index": 10,
        "label": "Number 1: Mosquito",
        "text": "And the most dangerous animal on Earth? The Mosquito. Responsible for over seven hundred thousand deaths every single year through malaria, dengue, and more. Size means nothing.",
    },
    {
        "index": 11,
        "label": "Outro",
        "text": "That was our Top 10 Most Dangerous Animals. Did your pick make the list? Like, subscribe, and hit the bell — the next countdown is one you do not want to miss.",
    },
]

# 3 seconds of silent audio per segment (keeps demo video short)
_SEGMENT_DURATION_S = 3.0

# ---------------------------------------------------------------------------
# Real audio generation via bundled ffmpeg
# ---------------------------------------------------------------------------


def _make_spoken_mp3(ffmpeg: str, out_path: Path, text: str) -> None:
    """
    Synthesize speech for `text` using macOS `say`, then convert to MP3.
    Falls back to a short silent tone if `say` is unavailable.
    """
    aiff = out_path.with_suffix(".aiff")
    try:
        subprocess.run(
            ["say", "-v", "Alex", text, "-o", str(aiff)],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            [ffmpeg, "-y", "-i", str(aiff), "-acodec", "libmp3lame", "-b:a", "128k", str(out_path)],
            check=True,
            capture_output=True,
        )
    finally:
        aiff.unlink(missing_ok=True)


def _measure_audio_duration(ffmpeg: str, path: Path) -> float:
    """Return audio duration in seconds using ffmpeg -f null."""
    try:
        result = subprocess.run(
            [ffmpeg, "-i", str(path), "-f", "null", "-"],
            capture_output=True,
            text=True,
        )
        # ffmpeg prints "Duration: HH:MM:SS.ss" to stderr
        for line in result.stderr.splitlines():
            if "Duration:" in line:
                dur_str = line.split("Duration:")[1].split(",")[0].strip()
                h, m, s = dur_str.split(":")
                return int(h) * 3600 + int(m) * 60 + float(s)
    except Exception:
        pass
    return 3.0  # fallback


def _concat_mp3s(ffmpeg: str, paths: list[Path], out_path: Path) -> None:
    """Concatenate MP3 files into one using ffmpeg concat demuxer."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        for p in paths:
            safe = str(p.resolve()).replace("'", "'\\''")
            f.write(f"file '{safe}'\n")
        list_file = f.name
    try:
        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                list_file,
                "-c",
                "copy",
                str(out_path),
            ],
            check=True,
            capture_output=True,
        )
    finally:
        Path(list_file).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Real image generation via PIL
# ---------------------------------------------------------------------------


def _make_placeholder_image(rank: int, title: str, width: int = 1280, height: int = 720) -> bytes:
    from PIL import Image, ImageDraw, ImageFont

    palette = [
        (15, 25, 80),
        (80, 15, 25),
        (25, 80, 15),
        (80, 60, 10),
        (10, 60, 80),
        (60, 15, 80),
        (80, 40, 10),
        (10, 80, 60),
        (60, 10, 40),
        (40, 10, 80),
    ]
    bg = palette[(rank - 1) % len(palette)]
    img = Image.new("RGB", (width, height), color=bg)
    draw = ImageDraw.Draw(img)

    # Subtle grid
    for x in range(0, width, 64):
        draw.line([(x, 0), (x, height)], fill=(255, 255, 255, 15), width=1)
    for y in range(0, height, 64):
        draw.line([(0, y), (width, y)], fill=(255, 255, 255, 15), width=1)

    # Load font
    font_big = font_med = None
    for fp in [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]:
        try:
            font_big = ImageFont.truetype(fp, 140)
            font_med = ImageFont.truetype(fp, 52)
            break
        except (OSError, IOError):
            pass
    if font_big is None:
        font_big = font_med = ImageFont.load_default()

    # Rank number (centered, large)
    rank_txt = f"#{rank}"
    bb = draw.textbbox((0, 0), rank_txt, font=font_big)
    rx = (width - (bb[2] - bb[0])) // 2
    ry = height // 2 - (bb[3] - bb[1]) // 2 - 40
    # Shadow
    draw.text((rx + 4, ry + 4), rank_txt, font=font_big, fill=(0, 0, 0))
    draw.text((rx, ry), rank_txt, font=font_big, fill=(255, 255, 255))

    # Title text (centered below rank)
    bb2 = draw.textbbox((0, 0), title, font=font_med)
    tx = (width - (bb2[2] - bb2[0])) // 2
    ty = ry + (bb[3] - bb[1]) + 24
    draw.text((tx + 2, ty + 2), title, font=font_med, fill=(0, 0, 0))
    draw.text((tx, ty), title, font=font_med, fill=(255, 230, 50))

    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Real video assembly via bundled ffmpeg (no moviepy needed)
# ---------------------------------------------------------------------------


def _assemble_video_ffmpeg(
    ffmpeg: str,
    image_paths: list[str],
    narration_mp3: str,
    out_path: Path,
    seg_duration: float,
    fps: int = 24,
) -> None:
    """
    Assemble a real playable MP4 from images + audio using ffmpeg directly.

    Strategy: ffmpeg concat demuxer (images shown for seg_duration each) +
    amix with narration audio, encoded to H.264/AAC.
    """
    # Build ffconcat file: each image shown for seg_duration seconds
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        for img in image_paths:
            safe = str(Path(img).resolve()).replace("'", "'\\''")
            f.write(f"file '{safe}'\n")
            f.write(f"duration {seg_duration:.3f}\n")
        # ffmpeg concat demuxer needs a trailing entry to set the last frame duration
        if image_paths:
            safe = str(Path(image_paths[-1]).resolve()).replace("'", "'\\''")
            f.write(f"file '{safe}'\n")
        list_file = f.name

    total_duration = seg_duration * len(image_paths)

    try:
        subprocess.run(
            [
                ffmpeg,
                "-y",
                # Video: loop images via concat demuxer
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                list_file,
                # Audio: narration
                "-i",
                narration_mp3,
                # Video filter: scale to 1280x720, set fps
                "-vf",
                f"scale=1280:720:force_original_aspect_ratio=decrease,"
                f"pad=1280:720:(ow-iw)/2:(oh-ih)/2,fps={fps}",
                # Encode
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-crf",
                "28",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                # Trim to narration length
                "-t",
                str(total_duration),
                "-shortest",
                str(out_path),
            ],
            check=True,
            capture_output=True,
        )
    finally:
        Path(list_file).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Pipeline mocks
# ---------------------------------------------------------------------------


def _make_voice_synthesize(ffmpeg: str):
    def fake_synthesize_segment(client, text, out_path, **kwargs):
        if not out_path.exists():
            _make_spoken_mp3(ffmpeg, out_path, text)

    return fake_synthesize_segment


def _make_get_audio_duration(ffmpeg: str):
    def fake_get_audio_duration_s(path: Path) -> float:
        return _measure_audio_duration(ffmpeg, path)

    return fake_get_audio_duration_s


def _make_voice_concat(ffmpeg: str):
    def fake_concat_segments(segment_paths, output_path):
        _concat_mp3s(ffmpeg, segment_paths, output_path)

    return fake_concat_segments


def _make_assembler_run(ffmpeg: str):
    def fake_assembler_run(
        image_paths, narration_mp3, captions, output_dir, config=None, music_path=None
    ):
        out_path = Path(output_dir) / "final_video.mp4"
        num = len(image_paths)
        if num == 0:
            raise ValueError("No images to assemble")
        total_dur = _measure_audio_duration(ffmpeg, Path(narration_mp3))
        seg_dur = total_dur / num
        logger.info("Assembling real MP4: %d images × %.1fs = %.1fs", num, seg_dur, total_dur)
        _assemble_video_ffmpeg(ffmpeg, image_paths, narration_mp3, out_path, seg_dur)
        logger.info("Real video written: %s", out_path)
        return out_path

    return fake_assembler_run


# ---------------------------------------------------------------------------
# Main demo runner
# ---------------------------------------------------------------------------


def run_demo(topic: str, clean: bool = False) -> None:
    ffmpeg = _get_ffmpeg()
    logger.info("Using ffmpeg: %s", ffmpeg)

    slug = topic.lower().replace(" ", "_")
    demo_output = PROJECT_ROOT / "demo" / "output" / slug

    if clean and demo_output.exists():
        shutil.rmtree(demo_output)
        logger.info("Cleaned: %s", demo_output)

    demo_output.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 60)
    logger.info("DEMO: Top 10 YouTube Pipeline")
    logger.info("Topic : %s", topic)
    logger.info("Output: %s", demo_output)
    logger.info("=" * 60)

    def fake_tavily_search(query, depth="advanced", max_results=10):
        return [
            {"title": f"Result {i}", "content": f"Facts about {query}"} for i in range(max_results)
        ]

    def fake_rank_with_claude(topic, search_text, model):
        return DEMO_RESEARCH_ITEMS

    def fake_generate_with_claude(research_items, model, words_per_segment):
        full = "\n\n".join(s["text"] for s in DEMO_SCRIPT_SEGMENTS)
        return {"full_script": full, "segments": DEMO_SCRIPT_SEGMENTS}

    def fake_make_elevenlabs_client():
        return MagicMock()

    def fake_get_audio_duration_s(path):
        return _measure_audio_duration(ffmpeg, Path(path))

    def fake_make_clients():
        return MagicMock(), MagicMock()

    def fake_generate_image_prompt(claude_client, item):
        return f"Dramatic cinematic shot of {item['title']}, 16:9 composition"

    def fake_generate_and_save_image(replicate_client, prompt, out_path, width=1280, height=720):
        rank_guess = int(out_path.stem.split("_")[-1]) if "_" in out_path.stem else 1
        title = next(
            (i["title"] for i in DEMO_RESEARCH_ITEMS if i["rank"] == rank_guess),
            out_path.stem,
        )
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(_make_placeholder_image(rank_guess, title, width, height))
        return out_path

    def fake_load_model(size):
        return MagicMock()

    def fake_whisper_transcribe(model, audio_path):
        total = _SEGMENT_DURATION_S * 12
        words = [
            "The",
            "mosquito",
            "is",
            "the",
            "most",
            "dangerous",
            "animal",
            "on",
            "Earth",
            "period",
        ]
        step = total / len(words)
        return {
            "segments": [
                {
                    "words": [
                        {"word": w, "start": i * step, "end": (i + 1) * step}
                        for i, w in enumerate(words)
                    ]
                }
            ]
        }

    def fake_captions_audio_duration(path):
        return _measure_audio_duration(ffmpeg, Path(path))

    whisper_mock = MagicMock()
    whisper_mock.load_model = fake_load_model
    whisper_mock.transcribe = fake_whisper_transcribe

    with (
        patch("modules.research.tavily_search", fake_tavily_search),
        patch("modules.research._rank_with_claude", fake_rank_with_claude),
        patch("modules.script._generate_with_claude", fake_generate_with_claude),
        patch("modules.voice._make_elevenlabs_client", fake_make_elevenlabs_client),
        patch("modules.voice._synthesize_segment", _make_voice_synthesize(ffmpeg)),
        patch("modules.voice._get_audio_duration_s", fake_get_audio_duration_s),
        patch("modules.voice._concatenate_segments", _make_voice_concat(ffmpeg)),
        patch("modules.visuals._make_clients", fake_make_clients),
        patch("modules.visuals._generate_image_prompt", fake_generate_image_prompt),
        patch("modules.visuals._generate_and_save_image", fake_generate_and_save_image),
        patch("modules.captions.whisper_timestamped", whisper_mock),
        patch("modules.captions.get_audio_duration", fake_captions_audio_duration),
        patch("modules.assembler.run", _make_assembler_run(ffmpeg)),
    ):
        from pipeline import Pipeline

        p = Pipeline(topic, demo_output)
        p.run()

    # Verify final_video.mp4 is a real file
    video_path = demo_output / "final_video.mp4"
    video_size = video_path.stat().st_size if video_path.exists() else 0

    artifacts = sorted(
        str(f.relative_to(demo_output)) for f in demo_output.rglob("*") if f.is_file()
    )
    summary = {
        "topic": topic,
        "output_dir": str(demo_output),
        "final_video": str(video_path),
        "final_video_size_kb": round(video_size / 1024, 1),
        "artifacts": artifacts,
        "note": (
            "Demo run — external APIs mocked (no keys needed). "
            "Images are PIL-generated placeholders. Audio narration uses macOS 'say' TTS (voice: Alex). "
            "final_video.mp4 is a real H.264/AAC video with audio, playable in any media player."
        ),
    }
    (demo_output / "demo_summary.json").write_text(json.dumps(summary, indent=2))

    logger.info("=" * 60)
    logger.info("DEMO COMPLETE — real playable video produced")
    logger.info("final_video.mp4: %s (%.1f KB)", video_path, video_size / 1024)
    logger.info("Artifacts: %s", demo_output)
    for f in artifacts:
        logger.info("  %s", f)
    logger.info("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run the Top 10 YouTube pipeline demo (no API keys needed). Produces a real playable MP4."
    )
    parser.add_argument(
        "--topic",
        default="Top 10 Dangerous Animals",
        help='Countdown topic (default: "Top 10 Dangerous Animals")',
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Delete existing demo output before running",
    )
    args = parser.parse_args()
    run_demo(args.topic, clean=args.clean)
