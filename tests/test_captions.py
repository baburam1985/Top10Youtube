"""Unit tests for modules/captions.py.

Contract: captions.run(narration_mp3_path, output_dir) → list of caption chunks:
  [{text: str, start: float, end: float}, ...]

Rules:
  - Every caption's start time >= 0
  - Every caption's end time <= audio duration
  - start < end for every chunk
  - No chunk spans more than 5 words
  - Output is written to output_dir/captions.json

whisper-timestamped is mocked to avoid model download.
"""

import json
from unittest.mock import patch

# Simulated whisper output — word-level segments
FAKE_WHISPER_RESULT = {
    "segments": [
        {
            "words": [
                {"word": "Welcome", "start": 0.0, "end": 0.5},
                {"word": "to", "start": 0.5, "end": 0.7},
                {"word": "our", "start": 0.7, "end": 0.9},
                {"word": "countdown", "start": 0.9, "end": 1.5},
                {"word": "of", "start": 1.5, "end": 1.7},
                {"word": "the", "start": 1.7, "end": 1.9},
                {"word": "Top", "start": 1.9, "end": 2.1},
                {"word": "Ten", "start": 2.1, "end": 2.4},
                {"word": "most", "start": 2.4, "end": 2.7},
                {"word": "dangerous", "start": 2.7, "end": 3.2},
            ]
        }
    ]
}

FAKE_AUDIO_DURATION = 5.0  # seconds


class TestCaptionTimestampsWithinAudioBounds:
    """Caption timestamps are valid and within audio bounds."""

    @patch("modules.captions.whisper_timestamped")
    @patch("modules.captions.get_audio_duration")
    def test_all_start_times_non_negative(
        self, mock_duration, mock_whisper, tmp_output_dir, fake_mp3
    ):
        """No caption chunk has a negative start time."""
        from modules.captions import run

        mock_duration.return_value = FAKE_AUDIO_DURATION
        mock_whisper.transcribe.return_value = FAKE_WHISPER_RESULT

        result = run(fake_mp3, tmp_output_dir)

        for chunk in result:
            assert chunk["start"] >= 0, f"Negative start time: {chunk}"

    @patch("modules.captions.whisper_timestamped")
    @patch("modules.captions.get_audio_duration")
    def test_all_end_times_within_audio_bounds(
        self, mock_duration, mock_whisper, tmp_output_dir, fake_mp3
    ):
        """No caption chunk end time exceeds the audio duration."""
        from modules.captions import run

        mock_duration.return_value = FAKE_AUDIO_DURATION
        mock_whisper.transcribe.return_value = FAKE_WHISPER_RESULT

        result = run(fake_mp3, tmp_output_dir)

        for chunk in result:
            assert (
                chunk["end"] <= FAKE_AUDIO_DURATION + 0.01
            ), f"end={chunk['end']} exceeds audio duration={FAKE_AUDIO_DURATION}: {chunk}"

    @patch("modules.captions.whisper_timestamped")
    @patch("modules.captions.get_audio_duration")
    def test_start_before_end_for_every_chunk(
        self, mock_duration, mock_whisper, tmp_output_dir, fake_mp3
    ):
        """start < end for every caption chunk."""
        from modules.captions import run

        mock_duration.return_value = FAKE_AUDIO_DURATION
        mock_whisper.transcribe.return_value = FAKE_WHISPER_RESULT

        result = run(fake_mp3, tmp_output_dir)

        for chunk in result:
            assert chunk["start"] < chunk["end"], f"start >= end in chunk: {chunk}"

    @patch("modules.captions.whisper_timestamped")
    @patch("modules.captions.get_audio_duration")
    def test_chunks_have_at_most_five_words(
        self, mock_duration, mock_whisper, tmp_output_dir, fake_mp3
    ):
        """No caption chunk contains more than 5 words."""
        from modules.captions import run

        mock_duration.return_value = FAKE_AUDIO_DURATION
        mock_whisper.transcribe.return_value = FAKE_WHISPER_RESULT

        result = run(fake_mp3, tmp_output_dir)

        for chunk in result:
            word_count = len(chunk["text"].split())
            assert (
                word_count <= 5
            ), f"Caption chunk has {word_count} words (max 5): '{chunk['text']}'"

    @patch("modules.captions.whisper_timestamped")
    @patch("modules.captions.get_audio_duration")
    def test_captions_json_written_to_output_dir(
        self, mock_duration, mock_whisper, tmp_output_dir, fake_mp3
    ):
        """captions.json is written to the output directory."""
        from modules.captions import run

        mock_duration.return_value = FAKE_AUDIO_DURATION
        mock_whisper.transcribe.return_value = FAKE_WHISPER_RESULT

        run(fake_mp3, tmp_output_dir)

        captions_path = tmp_output_dir / "captions.json"
        assert captions_path.exists()
        data = json.loads(captions_path.read_text())
        assert isinstance(data, list)
        assert len(data) > 0

    @patch("modules.captions.whisper_timestamped")
    @patch("modules.captions.get_audio_duration")
    def test_chunks_have_required_keys(self, mock_duration, mock_whisper, tmp_output_dir, fake_mp3):
        """Each caption chunk has text, start, and end keys."""
        from modules.captions import run

        mock_duration.return_value = FAKE_AUDIO_DURATION
        mock_whisper.transcribe.return_value = FAKE_WHISPER_RESULT

        result = run(fake_mp3, tmp_output_dir)

        for chunk in result:
            assert "text" in chunk
            assert "start" in chunk
            assert "end" in chunk

    @patch("modules.captions.whisper_timestamped")
    @patch("modules.captions.get_audio_duration")
    def test_non_overlapping_chunks(self, mock_duration, mock_whisper, tmp_output_dir, fake_mp3):
        """Caption chunks do not overlap (each start >= previous end)."""
        from modules.captions import run

        mock_duration.return_value = FAKE_AUDIO_DURATION
        mock_whisper.transcribe.return_value = FAKE_WHISPER_RESULT

        result = run(fake_mp3, tmp_output_dir)

        for i in range(1, len(result)):
            assert (
                result[i]["start"] >= result[i - 1]["end"] - 0.01
            ), f"Chunks overlap: {result[i-1]} and {result[i]}"
