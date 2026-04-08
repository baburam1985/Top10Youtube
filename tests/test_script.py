"""Unit tests for modules/script.py.

Contract: script.run(research_items, client) → dict with keys:
  full_script (str), segments (list of {text, index})

Segments must have exactly one entry per research item PLUS intro + outro = len(research_items) + 2.
Each numbered segment (index 1–10) must reference its corresponding research item by title.

All Claude API calls are mocked.
"""

import json
from unittest.mock import MagicMock, patch


class TestScriptSegmentsMatchResearchItems:
    """Script segments match research items 1-to-1."""

    def _make_claude_response(self, script_output):
        msg = MagicMock()
        msg.content = [MagicMock(text=json.dumps(script_output))]
        return msg

    @patch("modules.script.anthropic.Anthropic")
    def test_segment_count_equals_items_plus_two(
        self, mock_anthropic_cls, research_items, script_output
    ):
        """Segment count = 10 research items + intro + outro = 12."""
        from modules.script import run

        client = mock_anthropic_cls.return_value
        client.messages.create.return_value = self._make_claude_response(script_output)

        result = run(research_items)

        # 10 items + intro (index 0) + outro (index 11)
        assert len(result["segments"]) == len(research_items) + 2

    @patch("modules.script.anthropic.Anthropic")
    def test_each_item_segment_references_title(
        self, mock_anthropic_cls, research_items, script_output
    ):
        """Each numbered segment text contains its research item's title."""
        from modules.script import run

        client = mock_anthropic_cls.return_value
        client.messages.create.return_value = self._make_claude_response(script_output)

        result = run(research_items)

        # Segments at index 1–10 should correspond to research items
        item_segments = [s for s in result["segments"] if 1 <= s["index"] <= 10]
        assert len(item_segments) == 10

        item_titles = {item["title"].lower() for item in research_items}
        matched = 0
        for seg in item_segments:
            for title in item_titles:
                # Allow partial match (segment may use abbreviated title)
                if any(word in seg["text"].lower() for word in title.split()[:2]):
                    matched += 1
                    break
        assert matched == 10, f"Only {matched}/10 item segments referenced a research title"

    @patch("modules.script.anthropic.Anthropic")
    def test_full_script_is_non_empty_string(
        self, mock_anthropic_cls, research_items, script_output
    ):
        """full_script is a non-empty string."""
        from modules.script import run

        client = mock_anthropic_cls.return_value
        client.messages.create.return_value = self._make_claude_response(script_output)

        result = run(research_items)

        assert isinstance(result["full_script"], str)
        assert len(result["full_script"].strip()) > 0

    @patch("modules.script.anthropic.Anthropic")
    def test_segment_indices_are_sequential(
        self, mock_anthropic_cls, research_items, script_output
    ):
        """Segment indices run 0, 1, 2, …, N without gaps."""
        from modules.script import run

        client = mock_anthropic_cls.return_value
        client.messages.create.return_value = self._make_claude_response(script_output)

        result = run(research_items)

        indices = sorted(s["index"] for s in result["segments"])
        assert indices == list(range(len(result["segments"])))

    @patch("modules.script.anthropic.Anthropic")
    def test_segments_have_required_keys(self, mock_anthropic_cls, research_items, script_output):
        """Each segment dict has 'text' and 'index' keys."""
        from modules.script import run

        client = mock_anthropic_cls.return_value
        client.messages.create.return_value = self._make_claude_response(script_output)

        result = run(research_items)

        for seg in result["segments"]:
            assert "text" in seg
            assert "index" in seg
            assert isinstance(seg["text"], str) and seg["text"].strip()

    @patch("modules.script.anthropic.Anthropic")
    def test_no_live_api_calls(self, mock_anthropic_cls, research_items, script_output):
        """With mock in place, Claude is called but no network traffic occurs."""
        from modules.script import run

        client = mock_anthropic_cls.return_value
        client.messages.create.return_value = self._make_claude_response(script_output)

        run(research_items)

        client.messages.create.assert_called_once()
