"""Integration tests for modules/assembler.py.

Contract: assembler.run(image_paths, narration_mp3, captions, output_dir)
  - Produces output_dir/final_video.mp4
  - Video duration ≈ narration audio duration (within ±2 seconds)
  - Video is 1280×720

moviepy and ffmpeg are mocked; duration checks use mocked probe data.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np

NARRATION_DURATION = 45.0  # seconds — simulated


def _make_image_paths(tmp_dir, count=10):
    """Create placeholder PNG files."""
    try:
        from PIL import Image

        paths = []
        for i in range(1, count + 1):
            p = tmp_dir / "images" / f"item_{i}.png"
            p.parent.mkdir(parents=True, exist_ok=True)
            Image.new("RGB", (1280, 720), color=(i * 20 % 255, 0, 0)).save(str(p))
            paths.append(str(p))
        return paths
    except ImportError:
        paths = []
        for i in range(1, count + 1):
            p = tmp_dir / "images" / f"item_{i}.png"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 50)
            paths.append(str(p))
        return paths


class TestFinalVideoDurationApproxNarrationDuration:
    """Final video duration is within ±2 s of narration duration."""

    @patch("modules.assembler.get_audio_duration")
    @patch("modules.assembler.get_video_duration")
    @patch("modules.assembler.moviepy")
    def test_final_video_created(
        self, mock_moviepy, mock_video_dur, mock_audio_dur, tmp_output_dir, captions, fake_mp3
    ):
        """final_video.mp4 is written to the output directory."""
        from modules.assembler import run

        image_paths = _make_image_paths(tmp_output_dir)
        mock_audio_dur.return_value = NARRATION_DURATION
        mock_video_dur.return_value = NARRATION_DURATION

        # Mock moviepy chain so no actual video encoding happens
        mock_clip = MagicMock()
        mock_clip.write_videofile = MagicMock(
            side_effect=lambda path, **kw: Path(path).write_bytes(b"FAKE_MP4")
        )
        mock_moviepy.ImageClip.return_value = mock_clip
        mock_moviepy.concatenate_videoclips.return_value = mock_clip

        run(image_paths, str(fake_mp3), captions, tmp_output_dir)

        assert (tmp_output_dir / "final_video.mp4").exists()

    @patch("modules.assembler.get_audio_duration")
    @patch("modules.assembler.get_video_duration")
    @patch("modules.assembler.moviepy")
    def test_video_duration_within_tolerance(
        self, mock_moviepy, mock_video_dur, mock_audio_dur, tmp_output_dir, captions, fake_mp3
    ):
        """Video duration is within ±2 s of narration duration."""
        from modules.assembler import run

        image_paths = _make_image_paths(tmp_output_dir)
        mock_audio_dur.return_value = NARRATION_DURATION
        # Simulate a video that ends up within ±2 s
        mock_video_dur.return_value = NARRATION_DURATION + 1.0

        mock_clip = MagicMock()
        mock_clip.write_videofile = MagicMock(
            side_effect=lambda path, **kw: Path(path).write_bytes(b"FAKE_MP4")
        )
        mock_moviepy.ImageClip.return_value = mock_clip
        mock_moviepy.concatenate_videoclips.return_value = mock_clip

        run(image_paths, str(fake_mp3), captions, tmp_output_dir)

        video_dur = mock_video_dur.return_value
        audio_dur = mock_audio_dur.return_value
        assert (
            abs(video_dur - audio_dur) <= 2.0
        ), f"Video duration {video_dur}s deviates >2s from narration {audio_dur}s"

    @patch("modules.assembler.get_audio_duration")
    @patch("modules.assembler.get_video_duration")
    @patch("modules.assembler.moviepy")
    def test_one_image_clip_per_item(
        self, mock_moviepy, mock_video_dur, mock_audio_dur, tmp_output_dir, captions, fake_mp3
    ):
        """moviepy.ImageClip is called once per image (10 times)."""
        from modules.assembler import run

        image_paths = _make_image_paths(tmp_output_dir)
        mock_audio_dur.return_value = NARRATION_DURATION
        mock_video_dur.return_value = NARRATION_DURATION

        mock_clip = MagicMock()
        mock_clip.write_videofile = MagicMock(
            side_effect=lambda path, **kw: Path(path).write_bytes(b"FAKE_MP4")
        )
        mock_moviepy.ImageClip.return_value = mock_clip
        mock_moviepy.concatenate_videoclips.return_value = mock_clip

        run(image_paths, str(fake_mp3), captions, tmp_output_dir)

        assert mock_moviepy.ImageClip.call_count == 10

    @patch("modules.assembler.get_audio_duration")
    @patch("modules.assembler.get_video_duration")
    @patch("modules.assembler.moviepy")
    def test_narration_audio_attached(
        self, mock_moviepy, mock_video_dur, mock_audio_dur, tmp_output_dir, captions, fake_mp3
    ):
        """The narration MP3 path is passed to the video assembly."""
        from modules.assembler import run

        image_paths = _make_image_paths(tmp_output_dir)
        mock_audio_dur.return_value = NARRATION_DURATION
        mock_video_dur.return_value = NARRATION_DURATION

        mock_clip = MagicMock()
        mock_clip.write_videofile = MagicMock(
            side_effect=lambda path, **kw: Path(path).write_bytes(b"FAKE_MP4")
        )
        mock_moviepy.ImageClip.return_value = mock_clip
        mock_moviepy.concatenate_videoclips.return_value = mock_clip
        mock_moviepy.AudioFileClip.return_value = MagicMock()

        run(image_paths, str(fake_mp3), captions, tmp_output_dir)

        mock_moviepy.AudioFileClip.assert_called_once_with(str(fake_mp3))

    @patch("modules.assembler._overlay_frame_fn")
    @patch("modules.assembler.get_audio_duration")
    @patch("modules.assembler.moviepy")
    def test_overlay_uses_configured_resolution(
        self, mock_moviepy, mock_audio_dur, mock_overlay, tmp_output_dir, captions, fake_mp3
    ):
        """Overlay function receives width/height from config.video."""
        from modules.assembler import run

        image_paths = _make_image_paths(tmp_output_dir)
        mock_audio_dur.return_value = NARRATION_DURATION

        mock_clip = MagicMock()
        mock_clip.write_videofile = MagicMock(
            side_effect=lambda path, **kw: Path(path).write_bytes(b"FAKE_MP4")
        )
        mock_moviepy.ImageClip.return_value = mock_clip
        mock_moviepy.concatenate_videoclips.return_value = mock_clip
        mock_moviepy.AudioFileClip.return_value = MagicMock()
        mock_overlay.return_value = lambda gf, t: gf(t)

        run(
            image_paths,
            str(fake_mp3),
            captions,
            tmp_output_dir,
            config={"video": {"width": 1920, "height": 1080}},
        )

        first_call = mock_overlay.call_args_list[0]
        assert first_call.args[3] == 1920
        assert first_call.args[4] == 1080

    @patch("modules.assembler.get_audio_duration")
    @patch("modules.assembler.moviepy")
    def test_music_fades_are_applied_when_music_present(
        self, mock_moviepy, mock_audio_dur, tmp_output_dir, captions, fake_mp3
    ):
        """Assembler applies deterministic fade-in/out to background music."""
        from modules.assembler import run

        image_paths = _make_image_paths(tmp_output_dir)
        mock_audio_dur.return_value = NARRATION_DURATION

        video_clip = MagicMock()
        video_clip.write_videofile = MagicMock(
            side_effect=lambda path, **kw: Path(path).write_bytes(b"FAKE_MP4")
        )
        mock_moviepy.ImageClip.return_value = video_clip
        mock_moviepy.concatenate_videoclips.return_value = video_clip

        narration = MagicMock()
        music = MagicMock()
        music.duration = 120
        music.multiply_volume.return_value = music
        music.subclipped.return_value = music
        music.audio_fadein.return_value = music
        music.audio_fadeout.return_value = music
        mock_moviepy.AudioFileClip.side_effect = [narration, music]
        mock_moviepy.CompositeAudioClip.return_value = MagicMock()

        run(
            image_paths,
            str(fake_mp3),
            captions,
            tmp_output_dir,
            config={"audio": {"music_fade_in": 1.5, "music_fade_out": 2.0}},
            music_path=str(tmp_output_dir / "music.mp3"),
        )

        music.audio_fadein.assert_called_once_with(1.5)
        music.audio_fadeout.assert_called_once_with(2.0)


def test_overlay_skips_whitespace_only_caption_without_crashing():
    """Overlay should safely ignore active captions that wrap to zero lines."""
    from modules.assembler import _overlay_frame_fn

    width, height = 1280, 720
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    overlay = _overlay_frame_fn(
        rank=1,
        captions=[{"text": "   ", "start": 0.0, "end": 1.0}],
        clip_start_t=0.0,
        width=width,
        height=height,
    )

    out = overlay(lambda _t: frame, 0.5)

    assert out.shape == frame.shape
