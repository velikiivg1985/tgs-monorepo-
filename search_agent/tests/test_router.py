"""Tests for router.py — adaptive task classification."""
from __future__ import annotations
from unittest.mock import MagicMock
from tgs.router import classify_task

def _mock_client(response_json: str):
    client = MagicMock()
    choice = MagicMock(); choice.message.content = response_json
    resp = MagicMock(); resp.choices = [choice]
    client.chat.completions.create.return_value = resp
    return client

def test_router_factual():
    client = _mock_client('{"mode": "direct", "reason": "simple math"}')
    mode, _ = classify_task(client, "gpt-4o-mini", "Сколько будет 17*19?")
    assert mode == "direct"

def test_router_narrow_tech():
    client = _mock_client('{"mode": "light", "reason": "specific algorithm request"}')
    mode, _ = classify_task(client, "gpt-4o-mini", "Напиши функцию is_even на Python")
    assert mode == "light"

def test_router_open():
    client = _mock_client('{"mode": "full", "reason": "requires analyzing conflicting sources"}')
    mode, _ = classify_task(client, "gpt-4o-mini", "Влияет ли социальная сеть на уровень депрессии?")
    assert mode == "full"

def test_router_fallback():
    client = _mock_client('{"mode": "invalid_mode", "reason": "test"}')
    mode, reason = classify_task(client, "gpt-4o-mini", "test")
    assert mode == "full" # Fail-safe сработал
    assert "Fallback" in reason
