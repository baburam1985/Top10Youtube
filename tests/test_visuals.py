"""Integration tests for modules/visuals.py.

Contract: visuals.run(research_items, output_dir, replicate_client, claude_client)
  - Produces exactly 10 image files in output_dir/images/
  - Files named item_1.png … item_10.png (1280×720)
  - Returns list of 10 file paths

Replicate and Claude clients are mocked; image download is mocked.
"""

import io
from pathlib import Path
from unittest.mock import MagicMock, patch


def _make_fake_png_bytes(width=1280, height=720):
    """Return minimal valid PNG bytes at the given dimensions."""
    try:
        from PIL import Image

        buf = io.BytesIO()
        Image.new("RGB", (width, height), color=(0, 0, 0)).save(buf, format="PNG")
        return buf.getvalue()
    except ImportError:
        # Fallback: minimal PNG header (not a valid image, but enough for path checks)
        return b"\x89PNG\r\n\x1a\n" + b"\x00" * 100


class TestImagesProducedForAllTenItems:
    """visuals.run() produces exactly 10 image files."""

    def _setup_mocks(self, replicate_mock, claude_mock, tmp_output_dir):
        """Configure mocks so each Replicate call writes a fake PNG."""
        images_dir = tmp_output_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        fake_png = _make_fake_png_bytes()

        call_count = [0]

        def fake_replicate_run(*args, **kwargs):
            call_count[0] += 1
            rank = call_count[0]
            path = images_dir / f"item_{rank}.png"
            path.write_bytes(fake_png)
            return [f"file://{path}"]

        replicate_mock.run.side_effect = fake_replicate_run

        claude_msg = MagicMock()
        claude_msg.content = [MagicMock(text="A dramatic cinematic image of an animal")]
        claude_mock.messages.create.return_value = claude_msg

    @patch("modules.visuals.requests.get")
    def test_produces_ten_image_files(
        self, mock_get, research_items, tmp_output_dir, mock_replicate_client, mock_anthropic_client
    ):
        """Exactly 10 PNG files are created in output_dir/images/."""
        from modules.visuals import run

        fake_png = _make_fake_png_bytes()
        mock_get.return_value = MagicMock(status_code=200, content=fake_png)
        self._setup_mocks(mock_replicate_client, mock_anthropic_client, tmp_output_dir)

        run(research_items, tmp_output_dir, mock_replicate_client, mock_anthropic_client)

        images_dir = tmp_output_dir / "images"
        png_files = list(images_dir.glob("item_*.png"))
        assert len(png_files) == 10, f"Expected 10 PNG files, got {len(png_files)}"

    @patch("modules.visuals.requests.get")
    def test_returns_list_of_ten_paths(
        self, mock_get, research_items, tmp_output_dir, mock_replicate_client, mock_anthropic_client
    ):
        """run() returns a list of exactly 10 file path strings."""
        from modules.visuals import run

        fake_png = _make_fake_png_bytes()
        mock_get.return_value = MagicMock(status_code=200, content=fake_png)
        self._setup_mocks(mock_replicate_client, mock_anthropic_client, tmp_output_dir)

        result = run(research_items, tmp_output_dir, mock_replicate_client, mock_anthropic_client)

        assert isinstance(result, list)
        assert len(result) == 10

    @patch("modules.visuals.requests.get")
    def test_image_files_exist_on_disk(
        self, mock_get, research_items, tmp_output_dir, mock_replicate_client, mock_anthropic_client
    ):
        """Every path returned by run() exists on disk."""
        from modules.visuals import run

        fake_png = _make_fake_png_bytes()
        mock_get.return_value = MagicMock(status_code=200, content=fake_png)
        self._setup_mocks(mock_replicate_client, mock_anthropic_client, tmp_output_dir)

        result = run(research_items, tmp_output_dir, mock_replicate_client, mock_anthropic_client)

        for path in result:
            assert Path(path).exists(), f"Image path does not exist: {path}"

    @patch("modules.visuals.requests.get")
    def test_replicate_called_ten_times(
        self, mock_get, research_items, tmp_output_dir, mock_replicate_client, mock_anthropic_client
    ):
        """Replicate is called once per research item (10 total)."""
        from modules.visuals import run

        fake_png = _make_fake_png_bytes()
        mock_get.return_value = MagicMock(status_code=200, content=fake_png)
        self._setup_mocks(mock_replicate_client, mock_anthropic_client, tmp_output_dir)

        run(research_items, tmp_output_dir, mock_replicate_client, mock_anthropic_client)

        assert mock_replicate_client.run.call_count == 10

    @patch("modules.visuals.requests.get")
    def test_image_filenames_indexed_by_rank(
        self, mock_get, research_items, tmp_output_dir, mock_replicate_client, mock_anthropic_client
    ):
        """Images are named item_1.png through item_10.png."""
        from modules.visuals import run

        fake_png = _make_fake_png_bytes()
        mock_get.return_value = MagicMock(status_code=200, content=fake_png)
        self._setup_mocks(mock_replicate_client, mock_anthropic_client, tmp_output_dir)

        run(research_items, tmp_output_dir, mock_replicate_client, mock_anthropic_client)

        images_dir = tmp_output_dir / "images"
        for rank in range(1, 11):
            expected = images_dir / f"item_{rank}.png"
            assert expected.exists(), f"Missing image file: {expected.name}"
