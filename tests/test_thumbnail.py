"""Unit tests for modules/thumbnail.py.

Contract: thumbnail.run(item_1_image_path, topic, output_dir)
  - Produces output_dir/thumbnail.jpg
  - Dimensions exactly 1280×720
  - Contains visible text overlay (non-uniform pixel values)

No external APIs required. Uses Pillow only.
"""


import pytest

pytestmark = pytest.mark.skipif(
    not pytest.importorskip("PIL", reason="Pillow not installed"),
    reason="Pillow required for thumbnail tests",
)


@pytest.fixture
def item_1_image(tmp_output_dir):
    """Create a 1280×720 source image for the thumbnail."""
    from PIL import Image

    path = tmp_output_dir / "images" / "item_1.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (1280, 720), color=(50, 80, 120)).save(str(path))
    return path


class TestThumbnailDimensions:
    """thumbnail.run() produces a 1280×720 JPEG."""

    def test_thumbnail_file_created(self, item_1_image, tmp_output_dir, sample_topic):
        """thumbnail.jpg is written to the output directory."""
        from modules.thumbnail import run

        run(str(item_1_image), sample_topic, tmp_output_dir)

        assert (tmp_output_dir / "thumbnail.jpg").exists()

    def test_thumbnail_is_1280x720(self, item_1_image, tmp_output_dir, sample_topic):
        """Output thumbnail has dimensions exactly 1280×720."""
        from PIL import Image

        from modules.thumbnail import run

        run(str(item_1_image), sample_topic, tmp_output_dir)

        img = Image.open(tmp_output_dir / "thumbnail.jpg")
        assert img.size == (1280, 720), f"Expected (1280, 720), got {img.size}"

    def test_thumbnail_is_jpeg(self, item_1_image, tmp_output_dir, sample_topic):
        """Output file is a valid JPEG."""
        from PIL import Image

        from modules.thumbnail import run

        run(str(item_1_image), sample_topic, tmp_output_dir)

        img = Image.open(tmp_output_dir / "thumbnail.jpg")
        assert img.format == "JPEG"

    def test_thumbnail_has_text_overlay(self, item_1_image, tmp_output_dir, sample_topic):
        """Thumbnail pixels are not uniform — text or overlay was applied."""
        from PIL import Image

        from modules.thumbnail import run

        run(str(item_1_image), sample_topic, tmp_output_dir)

        img = Image.open(tmp_output_dir / "thumbnail.jpg").convert("L")
        arr = list(img.getdata())
        unique_values = len(set(arr))
        # A purely solid image would have 1 unique value; text adds many
        assert (
            unique_values > 10
        ), f"Thumbnail looks blank — only {unique_values} unique pixel values"

    def test_thumbnail_uses_item_1_as_base(self, tmp_output_dir, sample_topic):
        """Thumbnail base color reflects item_1 image content."""
        from PIL import Image

        from modules.thumbnail import run

        # Use a distinctive red source image
        red_path = tmp_output_dir / "images" / "item_1_red.png"
        red_path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (1280, 720), color=(200, 10, 10)).save(str(red_path))

        run(str(red_path), sample_topic, tmp_output_dir)

        img = Image.open(tmp_output_dir / "thumbnail.jpg").convert("RGB")
        # Sample a corner pixel — should carry red channel dominance from source
        pixels = list(img.getdata())
        red_dominant = sum(1 for r, g, b in pixels if r > g and r > b)
        total = len(pixels)
        # At least 30% of pixels should still carry red dominance
        assert (
            red_dominant / total >= 0.30
        ), "Thumbnail does not appear to derive from the source image"

    def test_run_is_idempotent(self, item_1_image, tmp_output_dir, sample_topic):
        """Calling run() twice overwrites thumbnail.jpg without error."""
        from modules.thumbnail import run

        run(str(item_1_image), sample_topic, tmp_output_dir)
        run(str(item_1_image), sample_topic, tmp_output_dir)

        assert (tmp_output_dir / "thumbnail.jpg").exists()
