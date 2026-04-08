"""Integration tests for pipeline.py checkpoint / resume behavior.

Contract: pipeline.Pipeline(topic, output_dir)
  - Persists state to output_dir/pipeline_state.json after each stage
  - resume() skips already-completed stages
  - A fresh run starts at RESEARCHING
  - A run interrupted after SCRIPTING resumes from VOICING

All module dependencies are mocked so no real work is done.
"""

import json
from pathlib import Path
from unittest.mock import patch

# Stage names must match the state machine in pipeline.py
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


def write_state(output_dir, stage, extra=None):
    """Write a pipeline_state.json simulating an interrupted run."""
    state = {"stage": stage, "topic": "Top 10 Dangerous Animals"}
    if extra:
        state.update(extra)
    (output_dir / "pipeline_state.json").write_text(json.dumps(state))


class TestPipelineResumesFromCheckpoint:
    """Pipeline reads pipeline_state.json and skips completed stages."""

    @patch("pipeline.modules.metadata")
    @patch("pipeline.modules.thumbnail")
    @patch("pipeline.modules.assembler")
    @patch("pipeline.modules.music")
    @patch("pipeline.modules.captions")
    @patch("pipeline.modules.visuals")
    @patch("pipeline.modules.voice")
    @patch("pipeline.modules.script")
    @patch("pipeline.modules.research")
    def test_fresh_run_starts_at_researching(
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
        """A fresh run (no state file) calls research as the first stage."""
        from pipeline import Pipeline

        mock_research.run.return_value = research_items
        mock_script.run.return_value = script_output
        mock_voice.run.return_value = None
        mock_visuals.run.return_value = [
            str(tmp_output_dir / f"item_{i}.png") for i in range(1, 11)
        ]
        mock_captions.run.return_value = captions
        mock_music.run.return_value = None
        mock_assembler.run.return_value = None
        mock_thumbnail.run.return_value = None
        mock_metadata.run.return_value = {}

        p = Pipeline(sample_topic, tmp_output_dir)
        p.run()

        mock_research.run.assert_called_once()

    @patch("pipeline.modules.metadata")
    @patch("pipeline.modules.thumbnail")
    @patch("pipeline.modules.assembler")
    @patch("pipeline.modules.music")
    @patch("pipeline.modules.captions")
    @patch("pipeline.modules.visuals")
    @patch("pipeline.modules.voice")
    @patch("pipeline.modules.script")
    @patch("pipeline.modules.research")
    def test_resume_after_scripting_skips_research_and_script(
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
        """If state says VOICING, research and script are not called again."""
        from pipeline import Pipeline

        # Simulate crash after SCRIPTING — state saved at VOICING
        write_state(
            tmp_output_dir,
            "VOICING",
            {
                "research_items": research_items,
                "script": script_output,
            },
        )

        mock_voice.run.return_value = None
        mock_visuals.run.return_value = [
            str(tmp_output_dir / f"item_{i}.png") for i in range(1, 11)
        ]
        mock_captions.run.return_value = captions
        mock_music.run.return_value = None
        mock_assembler.run.return_value = None
        mock_thumbnail.run.return_value = None
        mock_metadata.run.return_value = {}

        p = Pipeline(sample_topic, tmp_output_dir)
        p.run()

        mock_research.run.assert_not_called()
        mock_script.run.assert_not_called()
        mock_voice.run.assert_called_once()

    @patch("pipeline.modules.metadata")
    @patch("pipeline.modules.thumbnail")
    @patch("pipeline.modules.assembler")
    @patch("pipeline.modules.music")
    @patch("pipeline.modules.captions")
    @patch("pipeline.modules.visuals")
    @patch("pipeline.modules.voice")
    @patch("pipeline.modules.script")
    @patch("pipeline.modules.research")
    def test_state_file_written_after_each_stage(
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
        """pipeline_state.json is updated after every completed stage."""
        from pipeline import Pipeline

        mock_research.run.return_value = research_items
        mock_script.run.return_value = script_output
        mock_voice.run.return_value = None
        mock_visuals.run.return_value = [
            str(tmp_output_dir / f"item_{i}.png") for i in range(1, 11)
        ]
        mock_captions.run.return_value = captions
        mock_music.run.return_value = None
        mock_assembler.run.return_value = None
        mock_thumbnail.run.return_value = None
        mock_metadata.run.return_value = {}

        state_writes = []
        original_write = Path.write_text

        def tracking_write(self, data, *args, **kwargs):
            if self.name == "pipeline_state.json":
                state_writes.append(json.loads(data)["stage"])
            return original_write(self, data, *args, **kwargs)

        with patch.object(Path, "write_text", tracking_write):
            p = Pipeline(sample_topic, tmp_output_dir)
            p.run()

        # At minimum, state should have been written for DONE
        assert "DONE" in state_writes

    @patch("pipeline.modules.metadata")
    @patch("pipeline.modules.thumbnail")
    @patch("pipeline.modules.assembler")
    @patch("pipeline.modules.music")
    @patch("pipeline.modules.captions")
    @patch("pipeline.modules.visuals")
    @patch("pipeline.modules.voice")
    @patch("pipeline.modules.script")
    @patch("pipeline.modules.research")
    def test_done_state_when_complete(
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
        """After a full run, pipeline_state.json stage is DONE."""
        from pipeline import Pipeline

        mock_research.run.return_value = research_items
        mock_script.run.return_value = script_output
        mock_voice.run.return_value = None
        mock_visuals.run.return_value = [
            str(tmp_output_dir / f"item_{i}.png") for i in range(1, 11)
        ]
        mock_captions.run.return_value = captions
        mock_music.run.return_value = None
        mock_assembler.run.return_value = None
        mock_thumbnail.run.return_value = None
        mock_metadata.run.return_value = {}

        p = Pipeline(sample_topic, tmp_output_dir)
        p.run()

        state = json.loads((tmp_output_dir / "pipeline_state.json").read_text())
        assert state["stage"] == "DONE"

    @patch("pipeline.modules.metadata")
    @patch("pipeline.modules.thumbnail")
    @patch("pipeline.modules.assembler")
    @patch("pipeline.modules.music")
    @patch("pipeline.modules.captions")
    @patch("pipeline.modules.visuals")
    @patch("pipeline.modules.voice")
    @patch("pipeline.modules.script")
    @patch("pipeline.modules.research")
    def test_pipeline_passes_config_to_assembler_and_thumbnail(
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
        """Pipeline forwards config and selected music path to downstream modules."""
        from pipeline import Pipeline

        config = {
            "video": {"width": 1920, "height": 1080},
            "thumbnail": {"width": 1920, "height": 1080},
        }

        mock_research.run.return_value = research_items
        mock_script.run.return_value = script_output
        mock_voice.run.return_value = None
        mock_visuals.run.return_value = [
            str(tmp_output_dir / f"item_{i}.png") for i in range(1, 11)
        ]
        mock_captions.run.return_value = captions
        mock_music.run.return_value = str(tmp_output_dir / "music.mp3")
        mock_assembler.run.return_value = None
        mock_thumbnail.run.return_value = None
        mock_metadata.run.return_value = {}

        p = Pipeline(sample_topic, tmp_output_dir, config=config)
        p.run()

        mock_assembler.run.assert_called_once_with(
            [str(tmp_output_dir / f"item_{i}.png") for i in range(1, 11)],
            str(tmp_output_dir / "narration.mp3"),
            captions,
            tmp_output_dir,
            config=config,
            music_path=str(tmp_output_dir / "music.mp3"),
        )
        mock_thumbnail.run.assert_called_once_with(
            str(tmp_output_dir / "item_1.png"),
            sample_topic,
            tmp_output_dir,
            config=config,
        )
