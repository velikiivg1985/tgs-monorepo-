"""Tests for agent.py — integration tests with mocked externals."""
from __future__ import annotations
from tgs.agent import _extract_code

class TestExtractCode:
    def test_plain_code(self):
        assert _extract_code("print('hello')") == "print('hello')"
    def test_markdown_fence(self):
        assert _extract_code("```python\nprint('hello')\n```") == "print('hello')"
    def test_markdown_no_lang(self):
        assert _extract_code("```\nprint('hello')\n```") == "print('hello')"
    def test_multiple_blocks_takes_largest(self):
        raw = "```python\nx=1\n```\ntext\n```python\ndef f():\n    return 42\nprint(f())\n```"
        result = _extract_code(raw); assert "def f():" in result; assert "return 42" in result
    def test_with_explanation(self):
        raw = "Here is the code:\n```python\nprint('hi')\n```\nThis prints hi."
        assert _extract_code(raw) == "print('hi')"
