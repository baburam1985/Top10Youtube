"""
Pipeline Orchestrator — Top 10 YouTube

State machine:
    RESEARCHING → SCRIPTING → VOICING → GENERATING_VISUALS →
    CAPTIONING → SELECTING_MUSIC → ASSEMBLING → THUMBNAILING → METADATA → DONE

Checkpoint file: output_dir/pipeline_state.json
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Import all pipeline modules so they are accessible as pipeline.modules.X
import modules  # noqa: E402
import modules.assembler  # noqa: E402
import modules.captions  # noqa: E402
import modules.metadata  # noqa: E402
import modules.music  # noqa: E402
import modules.research  # noqa: E402
import modules.script  # noqa: E402
import modules.thumbnail  # noqa: E402
import modules.visuals  # noqa: E402
import modules.voice  # noqa: E402


class Pipeline:
    STAGES = [
        "RESEARCHING",
        "SCRIPTING",
        "VOICING",
        "GENERATING_VISUALS",
        "CAPTIONING",
        "SELECTING_MUSIC",
        "ASSEMBLING",
        "THUMBNAILING",
        "METADATA",
        "DONE",
    ]

    def __init__(self, topic: str, output_dir, config: dict | None = None) -> None:
        self.topic = topic
        self.output_dir = Path(output_dir)
        self.config = config or {}
        self._state_file = self.output_dir / "pipeline_state.json"

    # ------------------------------------------------------------------
    # Checkpoint helpers
    # ------------------------------------------------------------------

    def _load_state(self) -> dict:
        if self._state_file.exists():
            try:
                return json.loads(self._state_file.read_text())
            except Exception as exc:
                logger.warning("Could not load checkpoint: %s", exc)
        return {"stage": "RESEARCHING", "topic": self.topic}

    def _save_state(self, state: dict) -> None:
        self._state_file.write_text(json.dumps(state))

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def run(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        state = self._load_state()
        current = state.get("stage", "RESEARCHING")

        if current == "DONE":
            logger.info("Pipeline already DONE for '%s'.", self.topic)
            return

        # ── RESEARCHING ────────────────────────────────────────────────
        if current == "RESEARCHING":
            logger.info("Stage: RESEARCHING")
            research_items = modules.research.run(self.topic)
            state["research_items"] = research_items
            state["stage"] = "SCRIPTING"
            self._save_state(state)
            current = "SCRIPTING"

        # ── SCRIPTING ──────────────────────────────────────────────────
        if current == "SCRIPTING":
            logger.info("Stage: SCRIPTING")
            script = modules.script.run(state["research_items"])
            state["script"] = script
            state["stage"] = "VOICING"
            self._save_state(state)
            current = "VOICING"

        # ── VOICING ────────────────────────────────────────────────────
        if current == "VOICING":
            logger.info("Stage: VOICING")
            modules.voice.run(state["script"]["segments"], self.output_dir)
            state["stage"] = "GENERATING_VISUALS"
            self._save_state(state)
            current = "GENERATING_VISUALS"

        # ── GENERATING_VISUALS ─────────────────────────────────────────
        if current == "GENERATING_VISUALS":
            logger.info("Stage: GENERATING_VISUALS")
            image_paths = modules.visuals.run(state["research_items"], self.output_dir)
            state["image_paths"] = image_paths
            state["stage"] = "CAPTIONING"
            self._save_state(state)
            current = "CAPTIONING"

        # ── CAPTIONING ─────────────────────────────────────────────────
        if current == "CAPTIONING":
            logger.info("Stage: CAPTIONING")
            narration_path = str(self.output_dir / "narration.mp3")
            captions = modules.captions.run(narration_path, self.output_dir)
            state["captions"] = captions
            state["stage"] = "SELECTING_MUSIC"
            self._save_state(state)
            current = "SELECTING_MUSIC"

        # ── SELECTING_MUSIC ────────────────────────────────────────────
        if current == "SELECTING_MUSIC":
            logger.info("Stage: SELECTING_MUSIC")
            music_path = modules.music.run(None, self.output_dir)
            state["music_path"] = music_path
            state["stage"] = "ASSEMBLING"
            self._save_state(state)
            current = "ASSEMBLING"

        # ── ASSEMBLING ─────────────────────────────────────────────────
        if current == "ASSEMBLING":
            logger.info("Stage: ASSEMBLING")
            modules.assembler.run(
                state.get("image_paths", []),
                str(self.output_dir / "narration.mp3"),
                state.get("captions", []),
                self.output_dir,
                config=self.config,
                music_path=state.get("music_path"),
            )
            state["stage"] = "THUMBNAILING"
            self._save_state(state)
            current = "THUMBNAILING"

        # ── THUMBNAILING ───────────────────────────────────────────────
        if current == "THUMBNAILING":
            logger.info("Stage: THUMBNAILING")
            image_paths = state.get("image_paths", [])
            item_1_image = image_paths[0] if image_paths else ""
            modules.thumbnail.run(item_1_image, self.topic, self.output_dir, config=self.config)
            state["stage"] = "METADATA"
            self._save_state(state)
            current = "METADATA"

        # ── METADATA ───────────────────────────────────────────────────
        if current == "METADATA":
            logger.info("Stage: METADATA")
            modules.metadata.run(self.topic, state.get("script", {}), self.output_dir)
            state["stage"] = "DONE"
            self._save_state(state)

        logger.info("Pipeline DONE for '%s'.", self.topic)
