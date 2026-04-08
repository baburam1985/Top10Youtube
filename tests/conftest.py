"""Shared pytest fixtures for the Top 10 YouTube pipeline test suite."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def research_items():
    """10 structured research items as produced by modules/research.py."""
    with open(FIXTURES_DIR / "research_response.json") as f:
        return json.load(f)


@pytest.fixture
def script_output():
    """Full script output as produced by modules/script.py."""
    with open(FIXTURES_DIR / "script_response.json") as f:
        return json.load(f)


@pytest.fixture
def captions():
    """Caption chunks as produced by modules/captions.py."""
    with open(FIXTURES_DIR / "captions.json") as f:
        return json.load(f)


@pytest.fixture
def tmp_output_dir():
    """Temporary output directory cleaned up after each test."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def sample_topic():
    return "Top 10 Dangerous Animals"


@pytest.fixture
def sample_topic_slug():
    return "top_10_dangerous_animals"


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client that returns a structured 10-item list."""
    client = MagicMock()
    message = MagicMock()
    message.content = [MagicMock(text="mocked claude response")]
    client.messages.create.return_value = message
    return client


@pytest.fixture
def mock_elevenlabs_client():
    """Mock ElevenLabs client that returns fake audio bytes."""
    client = MagicMock()
    client.generate.return_value = iter([b"FAKE_AUDIO_DATA"] * 3)
    return client


@pytest.fixture
def mock_replicate_client():
    """Mock Replicate client that returns a fake image URL."""
    mock = MagicMock()
    mock.run.return_value = ["https://example.com/fake_image.png"]
    return mock


@pytest.fixture
def fake_mp3(tmp_output_dir):
    """Write a minimal valid-looking mp3 placeholder file."""
    path = tmp_output_dir / "narration.mp3"
    path.write_bytes(b"\xff\xfb\x90\x00" * 256)  # fake MP3 frames
    return path


@pytest.fixture
def fake_image(tmp_output_dir):
    """Write a 1280x720 PNG using Pillow."""
    pytest.importorskip("PIL")
    from PIL import Image

    img = Image.new("RGB", (1280, 720), color=(30, 30, 30))
    path = tmp_output_dir / "item_1.png"
    img.save(str(path))
    return path
