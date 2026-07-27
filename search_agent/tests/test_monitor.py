"""Tests for monitor.py with mocked LLM."""
from __future__ import annotations
from unittest.mock import MagicMock
from tgs.monitor import ask, Signal, _parse
from tgs.search import Page

class TestParse:
    def test_direct_json(self):
        raw = '{"blind_spot": "x", "invariant": "y", "done": true, "falsification": "z"}'
        result = _parse(raw); assert result["invariant"] == "y"; assert result["done"] is True
    def test_json_in_markdown(self):
        raw = '```json\n{"invariant": "test", "done": false}\n```'
        result = _parse(raw); assert result["invariant"] == "test"
    def test_json_with_prefix(self):
        raw = 'Here is my analysis:\n{"invariant": "test", "done": true}'
        result = _parse(raw); assert result["invariant"] == "test"
    def test_broken_json(self):
        result = _parse("this is not json at all"); assert result == {}
    def test_empty(self):
        assert _parse("") == {}

class TestAskWithMock:
    def _mock_client(self, response_text: str):
        client = MagicMock()
        choice = MagicMock(); choice.message.content = response_text
        resp = MagicMock(); resp.choices = [choice]
        client.chat.completions.create.return_value = resp
        return client

    def test_returns_signal(self):
        client = self._mock_client('{"blind_spot": "framing", "invariant": "conflict", "retract": null, "geometry_changed": true, "next_query": null, "done": true, "falsification": "if no conflict exists"}')
        page = Page(title="Test", url="http://test", body="some page text")
        signal = ask(client, "gpt-4o-mini", "test?", [], [page])
        assert isinstance(signal, Signal); assert signal.invariant == "conflict"; assert signal.done is True; assert signal.falsification == "if no conflict exists"

    def test_handles_llm_failure(self):
        client = MagicMock(); client.chat.completions.create.side_effect = Exception("API down")
        signal = ask(client, "gpt-4o-mini", "test?", [], [])
        assert isinstance(signal, Signal); assert signal.invariant is None; assert signal.done is False
