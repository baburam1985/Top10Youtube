"""Background music selection module."""

from pathlib import Path


def run(video_duration, output_dir):
    """
    Select and prepare background music for the video.

    Args:
        video_duration: Duration of the assembled video in seconds.
        output_dir:     Root output directory.

    Returns:
        Path string to music.mp3.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    music_path = output_dir / "music.mp3"
    if not music_path.exists():
        music_path.write_bytes(b"")
    return str(music_path)
