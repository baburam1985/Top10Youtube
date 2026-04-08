"""Regression coverage for render/publish failure recovery.

These tests verify that restart semantics recover cleanly from late-stage
failures without re-running already completed early stages.
"""

import json
from unittest.mock import patch


def _write_state(output_dir, stage, **state):
    payload = {"stage": stage, "topic": "Top 10 Dangerous Animals"}
    payload.update(state)
    (output_dir / "pipeline_state.json").write_text(json.dumps(payload))


def _ready_for_assembly_state(tmp_output_dir, research_items, script_output, captions):
    return {
        "research_items": research_items,
        "script": script_output,
        "image_paths": [str(tmp_output_dir / f"item_{i}.png") for i in range(1, 11)],
        "captions": captions,
        "music_path": str(tmp_output_dir / "music.mp3"),
    }


class TestRenderPublishRecovery:
    @patch("pipeline.modules.metadata.run")
    @patch("pipeline.modules.thumbnail.run")
    @patch("pipeline.modules.assembler.run")
    @patch("pipeline.modules.music.run")
    @patch("pipeline.modules.captions.run")
    @patch("pipeline.modules.visuals.run")
    @patch("pipeline.modules.voice.run")
    @patch("pipeline.modules.script.run")
    @patch("pipeline.modules.research.run")
    def test_resume_from_assembling_after_render_failure(
        self,
        mock_research,
        mock_script,
        mock_voice,
        mock_visuals,
        mock_captions,
        mock_music,
        mock_assembler,
        mock_thumbnail,
        mock_metadata,
        tmp_output_dir,
        sample_topic,
        research_items,
        script_output,
        captions,
    ):
        from pipeline import Pipeline

        _write_state(
            tmp_output_dir,
            "ASSEMBLING",
            **_ready_for_assembly_state(tmp_output_dir, research_items, script_output, captions),
        )

        mock_assembler.side_effect = RuntimeError("ffmpeg render failed")
        p = Pipeline(sample_topic, tmp_output_dir)

        try:
            p.run()
        except RuntimeError:
            pass

        state_after_failure = json.loads((tmp_output_dir / "pipeline_state.json").read_text())
        assert state_after_failure["stage"] == "ASSEMBLING"

        mock_assembler.side_effect = None
        mock_assembler.return_value = None
        mock_thumbnail.return_value = None
        mock_metadata.return_value = {}

        p.run()

        final_state = json.loads((tmp_output_dir / "pipeline_state.json").read_text())
        assert final_state["stage"] == "DONE"
        mock_research.run.assert_not_called()
        mock_script.run.assert_not_called()

    @patch("pipeline.modules.metadata.run")
    @patch("pipeline.modules.thumbnail.run")
    @patch("pipeline.modules.assembler.run")
    @patch("pipeline.modules.music.run")
    @patch("pipeline.modules.captions.run")
    @patch("pipeline.modules.visuals.run")
    @patch("pipeline.modules.voice.run")
    @patch("pipeline.modules.script.run")
    @patch("pipeline.modules.research.run")
    def test_resume_from_metadata_after_publish_failure(
        self,
        mock_research,
        mock_script,
        mock_voice,
        mock_visuals,
        mock_captions,
        mock_music,
        mock_assembler,
        mock_thumbnail,
        mock_metadata,
        tmp_output_dir,
        sample_topic,
        research_items,
        script_output,
        captions,
    ):
        from pipeline import Pipeline

        _write_state(
            tmp_output_dir,
            "METADATA",
            **_ready_for_assembly_state(tmp_output_dir, research_items, script_output, captions),
        )

        mock_metadata.side_effect = RuntimeError("metadata publish failed")
        p = Pipeline(sample_topic, tmp_output_dir)

        try:
            p.run()
        except RuntimeError:
            pass

        state_after_failure = json.loads((tmp_output_dir / "pipeline_state.json").read_text())
        assert state_after_failure["stage"] == "METADATA"

        mock_metadata.side_effect = None
        mock_metadata.return_value = {}
        p.run()

        final_state = json.loads((tmp_output_dir / "pipeline_state.json").read_text())
        assert final_state["stage"] == "DONE"
        mock_assembler.run.assert_not_called()
        mock_thumbnail.run.assert_not_called()
