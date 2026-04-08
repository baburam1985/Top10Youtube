"""End-to-end smoke test for the Top 10 YouTube pipeline.

Invokes `python run.py --topic "..."` with ALL external APIs mocked.
Verifies that the full output bundle is produced:
  - final_video.mp4
  - thumbnail.jpg
  - metadata.json

No live network calls are made.
"""

import json
from pathlib import Path
from unittest.mock import patch

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────


def _stub_research(topic, *args, **kwargs):
    return [
        {"rank": i, "title": f"Animal {i}", "facts": f"Fact {i}", "hook_line": f"Hook {i}"}
        for i in range(1, 11)
    ]


def _stub_script(research_items, *args, **kwargs):
    segments = [{"text": "Intro hook.", "index": 0}]
    for item in research_items:
        segments.append(
            {
                "text": f"Number {item['rank']}: {item['title']}. {item['hook_line']}",
                "index": item["rank"],
            }
        )
    segments.append({"text": "Like and subscribe!", "index": 11})
    return {"full_script": " ".join(s["text"] for s in segments), "segments": segments}


def _stub_voice(segments, output_dir, *args, **kwargs):
    output_dir = Path(output_dir)
    (output_dir / "segments").mkdir(parents=True, exist_ok=True)
    for seg in segments:
        (output_dir / "segments" / f"segment_{seg['index']}.mp3").write_bytes(b"FAKE_MP3")
    (output_dir / "narration.mp3").write_bytes(b"FAKE_MP3")
    timestamps = {str(seg["index"]): seg["index"] * 4.0 for seg in segments}
    (output_dir / "segment_timestamps.json").write_text(json.dumps(timestamps))


def _stub_visuals(research_items, output_dir, *args, **kwargs):
    output_dir = Path(output_dir)
    images_dir = output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for item in research_items:
        p = images_dir / f"item_{item['rank']}.png"
        p.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 50)
        paths.append(str(p))
    return paths


def _stub_captions(narration_path, output_dir, *args, **kwargs):
    output_dir = Path(output_dir)
    chunks = [{"text": "Welcome to", "start": 0.0, "end": 1.0}]
    (output_dir / "captions.json").write_text(json.dumps(chunks))
    return chunks


def _stub_music(video_duration, output_dir, *args, **kwargs):
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    (Path(output_dir) / "music.mp3").write_bytes(b"FAKE_MUSIC")


def _stub_assembler(image_paths, narration, captions, output_dir, *args, **kwargs):
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    (Path(output_dir) / "final_video.mp4").write_bytes(b"FAKE_MP4")


def _stub_thumbnail(image_path, topic, output_dir, *args, **kwargs):
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    try:
        from PIL import Image

        img = Image.new("RGB", (1280, 720), color=(10, 10, 10))
        img.save(str(Path(output_dir) / "thumbnail.jpg"), "JPEG")
    except ImportError:
        (Path(output_dir) / "thumbnail.jpg").write_bytes(b"FAKE_JPG")


def _stub_metadata(topic, script, output_dir, *args, **kwargs):
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    meta = {
        "title": f"{topic} - Top 10 Countdown",
        "description": "Watch our epic countdown!",
        "tags": ["top10", "animals", "countdown"],
    }
    (Path(output_dir) / "metadata.json").write_text(json.dumps(meta))
    return meta


# ──────────────────────────────────────────────────────────────────────────────
# Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestEndToEndSmoke:
    """Full pipeline smoke test — all APIs mocked, no live network calls."""

    TOPIC = "Top 10 Dangerous Animals"

    def _run_pipeline_with_stubs(self, tmp_output_dir):
        """Import and invoke pipeline.Pipeline with all modules stubbed."""
        with (
            patch("modules.research.run", side_effect=_stub_research),
            patch("modules.script.run", side_effect=_stub_script),
            patch("modules.voice.run", side_effect=_stub_voice),
            patch("modules.visuals.run", side_effect=_stub_visuals),
            patch("modules.captions.run", side_effect=_stub_captions),
            patch("modules.music.run", side_effect=_stub_music),
            patch("modules.assembler.run", side_effect=_stub_assembler),
            patch("modules.thumbnail.run", side_effect=_stub_thumbnail),
            patch("modules.metadata.run", side_effect=_stub_metadata),
        ):
            from pipeline import Pipeline

            p = Pipeline(self.TOPIC, tmp_output_dir)
            p.run()

    def test_final_video_produced(self, tmp_output_dir):
        """E2E: final_video.mp4 exists after a full pipeline run."""
        self._run_pipeline_with_stubs(tmp_output_dir)
        assert (tmp_output_dir / "final_video.mp4").exists()

    def test_thumbnail_produced(self, tmp_output_dir):
        """E2E: thumbnail.jpg exists after a full pipeline run."""
        self._run_pipeline_with_stubs(tmp_output_dir)
        assert (tmp_output_dir / "thumbnail.jpg").exists()

    def test_metadata_produced(self, tmp_output_dir):
        """E2E: metadata.json exists and has title, description, tags."""
        self._run_pipeline_with_stubs(tmp_output_dir)
        meta_path = tmp_output_dir / "metadata.json"
        assert meta_path.exists()
        meta = json.loads(meta_path.read_text())
        assert "title" in meta
        assert "description" in meta
        assert "tags" in meta

    def test_pipeline_state_is_done(self, tmp_output_dir):
        """E2E: pipeline_state.json stage == DONE at completion."""
        self._run_pipeline_with_stubs(tmp_output_dir)
        state_path = tmp_output_dir / "pipeline_state.json"
        assert state_path.exists()
        state = json.loads(state_path.read_text())
        assert state["stage"] == "DONE"

    def test_ten_segment_mp3s_produced(self, tmp_output_dir):
        """E2E: segment MP3 files are produced for all 12 segments (10 items + intro + outro)."""
        self._run_pipeline_with_stubs(tmp_output_dir)
        seg_dir = tmp_output_dir / "segments"
        mp3s = list(seg_dir.glob("segment_*.mp3"))
        assert len(mp3s) == 12  # intro + 10 items + outro

    def test_ten_images_produced(self, tmp_output_dir):
        """E2E: item_1.png through item_10.png are present in images/."""
        self._run_pipeline_with_stubs(tmp_output_dir)
        images_dir = tmp_output_dir / "images"
        for rank in range(1, 11):
            assert (images_dir / f"item_{rank}.png").exists(), f"Missing image: item_{rank}.png"

    def test_no_live_api_keys_required(self, tmp_output_dir, monkeypatch):
        """E2E: pipeline completes even when API env vars are absent."""
        monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
        monkeypatch.delenv("REPLICATE_API_TOKEN", raising=False)
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        # Should not raise because all modules are stubbed
        self._run_pipeline_with_stubs(tmp_output_dir)
        assert (tmp_output_dir / "final_video.mp4").exists()

    def test_metadata_tags_is_list(self, tmp_output_dir):
        """E2E: metadata tags field is a non-empty list."""
        self._run_pipeline_with_stubs(tmp_output_dir)
        meta = json.loads((tmp_output_dir / "metadata.json").read_text())
        assert isinstance(meta["tags"], list)
        assert len(meta["tags"]) > 0
