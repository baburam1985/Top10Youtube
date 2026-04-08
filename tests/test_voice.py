"""Integration tests for modules/voice.py.

Contract: voice.run(segments, output_dir, client) produces:
  - One .mp3 file per segment in output_dir/segments/
  - A merged narration.mp3 in output_dir/
  - A segment_timestamps.json mapping segment index → start time (seconds)

ElevenLabs client is mocked; ffmpeg subprocess is mocked.
"""

import json
from unittest.mock import MagicMock, patch


class TestVoiceFilesProducedForAllSegments:
    """Voice synthesis produces one audio file per script segment."""

    def _mock_elevenlabs(self, audio_bytes=b"FAKE_MP3_DATA"):
        client = MagicMock()
        client.generate.return_value = iter([audio_bytes])
        return client

    @patch("modules.voice.subprocess.run")
    def test_segment_mp3s_created(self, mock_subprocess, script_output, tmp_output_dir):
        """An .mp3 file is created for every segment."""
        from modules.voice import run

        mock_subprocess.return_value = MagicMock(returncode=0)
        client = self._mock_elevenlabs()

        run(script_output["segments"], tmp_output_dir, client)

        seg_dir = tmp_output_dir / "segments"
        mp3_files = list(seg_dir.glob("segment_*.mp3"))
        assert len(mp3_files) == len(
            script_output["segments"]
        ), f"Expected {len(script_output['segments'])} segment MP3s, found {len(mp3_files)}"

    @patch("modules.voice.subprocess.run")
    def test_narration_mp3_created(self, mock_subprocess, script_output, tmp_output_dir):
        """Merged narration.mp3 is written to the output directory."""
        from modules.voice import run

        mock_subprocess.return_value = MagicMock(returncode=0)
        client = self._mock_elevenlabs()

        run(script_output["segments"], tmp_output_dir, client)

        assert (tmp_output_dir / "narration.mp3").exists()

    @patch("modules.voice.subprocess.run")
    def test_segment_timestamps_json_created(self, mock_subprocess, script_output, tmp_output_dir):
        """segment_timestamps.json is written with one entry per segment."""
        from modules.voice import run

        mock_subprocess.return_value = MagicMock(returncode=0)
        client = self._mock_elevenlabs()

        run(script_output["segments"], tmp_output_dir, client)

        ts_path = tmp_output_dir / "segment_timestamps.json"
        assert ts_path.exists()
        timestamps = json.loads(ts_path.read_text())
        assert len(timestamps) == len(script_output["segments"])

    @patch("modules.voice.subprocess.run")
    def test_timestamps_are_non_negative(self, mock_subprocess, script_output, tmp_output_dir):
        """All segment start times are >= 0."""
        from modules.voice import run

        mock_subprocess.return_value = MagicMock(returncode=0)
        client = self._mock_elevenlabs()

        run(script_output["segments"], tmp_output_dir, client)

        ts_path = tmp_output_dir / "segment_timestamps.json"
        timestamps = json.loads(ts_path.read_text())
        for idx, start in timestamps.items():
            assert start >= 0, f"Segment {idx} has negative start time {start}"

    @patch("modules.voice.subprocess.run")
    def test_elevenlabs_called_per_segment(self, mock_subprocess, script_output, tmp_output_dir):
        """ElevenLabs generate() is called once per segment."""
        from modules.voice import run

        mock_subprocess.return_value = MagicMock(returncode=0)
        client = self._mock_elevenlabs()

        run(script_output["segments"], tmp_output_dir, client)

        assert client.generate.call_count == len(script_output["segments"])

    @patch("modules.voice.subprocess.run")
    def test_ffmpeg_called_for_merge(self, mock_subprocess, script_output, tmp_output_dir):
        """ffmpeg is invoked to merge segment MP3s into narration.mp3."""
        from modules.voice import run

        mock_subprocess.return_value = MagicMock(returncode=0)
        client = self._mock_elevenlabs()

        run(script_output["segments"], tmp_output_dir, client)

        assert mock_subprocess.called
        # At least one call should involve ffmpeg
        any_ffmpeg = any("ffmpeg" in str(c.args[0]) for c in mock_subprocess.call_args_list)
        assert any_ffmpeg, "Expected ffmpeg to be called for audio merge"
