"""Unit tests for modules/research.py.

Contract: research.run(topic, client) → List[dict] with exactly 10 items,
each having keys: rank, title, facts, hook_line.

All external I/O (Tavily, Claude) is mocked.
"""

import json
from unittest.mock import MagicMock, patch


class TestResearchReturnsExactlyTenItems:
    """Research returns exactly 10 structured items."""

    def _make_claude_response(self, items):
        """Build a mock Anthropic Message whose content is JSON-encoded items."""
        msg = MagicMock()
        msg.content = [MagicMock(text=json.dumps(items))]
        return msg

    def _make_ten_items(self):
        return [
            {"rank": i, "title": f"Item {i}", "facts": f"Fact {i}", "hook_line": f"Hook {i}"}
            for i in range(1, 11)
        ]

    @patch("modules.research.tavily_search")
    @patch("modules.research.anthropic.Anthropic")
    def test_returns_list_of_ten(self, mock_anthropic_cls, mock_tavily, research_items):
        """run() returns a list of exactly 10 items."""
        from modules.research import run

        mock_tavily.return_value = [{"title": "t", "content": "c"}] * 20
        client = mock_anthropic_cls.return_value
        client.messages.create.return_value = self._make_claude_response(research_items)

        result = run("Top 10 Dangerous Animals")

        assert isinstance(result, list)
        assert len(result) == 10

    @patch("modules.research.tavily_search")
    @patch("modules.research.anthropic.Anthropic")
    def test_items_have_required_keys(self, mock_anthropic_cls, mock_tavily, research_items):
        """Each item has rank, title, facts, and hook_line."""
        from modules.research import run

        mock_tavily.return_value = [{"title": "t", "content": "c"}] * 20
        client = mock_anthropic_cls.return_value
        client.messages.create.return_value = self._make_claude_response(research_items)

        result = run("Top 10 Dangerous Animals")

        required_keys = {"rank", "title", "facts", "hook_line"}
        for item in result:
            assert required_keys.issubset(
                item.keys()
            ), f"Item missing keys: {required_keys - item.keys()}"

    @patch("modules.research.tavily_search")
    @patch("modules.research.anthropic.Anthropic")
    def test_ranks_are_one_through_ten(self, mock_anthropic_cls, mock_tavily, research_items):
        """Ranks are integers 1–10."""
        from modules.research import run

        mock_tavily.return_value = [{"title": "t", "content": "c"}] * 20
        client = mock_anthropic_cls.return_value
        client.messages.create.return_value = self._make_claude_response(research_items)

        result = run("Top 10 Dangerous Animals")

        ranks = sorted(item["rank"] for item in result)
        assert ranks == list(range(1, 11))

    @patch("modules.research.tavily_search")
    @patch("modules.research.anthropic.Anthropic")
    def test_titles_are_non_empty_strings(self, mock_anthropic_cls, mock_tavily, research_items):
        """Every item title is a non-empty string."""
        from modules.research import run

        mock_tavily.return_value = [{"title": "t", "content": "c"}] * 20
        client = mock_anthropic_cls.return_value
        client.messages.create.return_value = self._make_claude_response(research_items)

        result = run("Top 10 Dangerous Animals")

        for item in result:
            assert isinstance(item["title"], str) and item["title"].strip()

    @patch("modules.research.tavily_search")
    @patch("modules.research.anthropic.Anthropic")
    def test_no_duplicate_ranks(self, mock_anthropic_cls, mock_tavily, research_items):
        """No duplicate rank values in the result."""
        from modules.research import run

        mock_tavily.return_value = [{"title": "t", "content": "c"}] * 20
        client = mock_anthropic_cls.return_value
        client.messages.create.return_value = self._make_claude_response(research_items)

        result = run("Top 10 Dangerous Animals")

        ranks = [item["rank"] for item in result]
        assert len(ranks) == len(set(ranks))

    @patch("modules.research.tavily_search")
    @patch("modules.research.anthropic.Anthropic")
    def test_calls_tavily_once(self, mock_anthropic_cls, mock_tavily, research_items):
        """Tavily is called exactly once per run() invocation."""
        from modules.research import run

        mock_tavily.return_value = [{"title": "t", "content": "c"}] * 20
        client = mock_anthropic_cls.return_value
        client.messages.create.return_value = self._make_claude_response(research_items)

        run("Top 10 Dangerous Animals")

        mock_tavily.assert_called_once()

    @patch("modules.research.tavily_search")
    @patch("modules.research.anthropic.Anthropic")
    def test_no_live_api_calls_without_mock(self, mock_anthropic_cls, mock_tavily, research_items):
        """With mocks in place, no real network calls are made."""
        from modules.research import run

        mock_tavily.return_value = [{"title": "t", "content": "c"}] * 20
        client = mock_anthropic_cls.return_value
        client.messages.create.return_value = self._make_claude_response(research_items)

        # Should complete without error (no network)
        result = run("Top 10 Dangerous Animals")
        assert len(result) == 10
