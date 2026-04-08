"""Thumbnail generation module."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def run(image_path, topic, output_dir):
    """
    Composite a 1280x720 thumbnail JPEG with bold text overlay.

    Args:
        image_path: Path to source image (item_1.png).
        topic:      Countdown topic string used for the title text.
        output_dir: Directory where thumbnail.jpg is written.

    Returns:
        Path string to thumbnail.jpg.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    img = Image.open(image_path).convert("RGB")
    img = img.resize((1280, 720), Image.LANCZOS)

    draw = ImageDraw.Draw(img)

    # Try system fonts; fall back to PIL default
    font = None
    for font_path in [
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    ]:
        try:
            font = ImageFont.truetype(font_path, 72)
            break
        except (OSError, IOError):
            continue
    if font is None:
        font = ImageFont.load_default()

    text = topic.upper()
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = max(0, (1280 - text_w) // 2)
    y = max(0, 720 - text_h - 60)

    # Drop shadow
    draw.text((x + 3, y + 3), text, fill=(0, 0, 0), font=font)
    # Main text in yellow
    draw.text((x, y), text, fill=(255, 255, 0), font=font)

    thumbnail_path = output_dir / "thumbnail.jpg"
    img.save(str(thumbnail_path), "JPEG", quality=90)
    return str(thumbnail_path)
