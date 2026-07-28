"""
Tests for probe-based routing in agent.py.
No network. No LLM. Mocked signals.
"""
from __future__ import annotations
from unittest.mock import MagicMock
from tgs.agent import TGSAgent
from tgs.monitor import Signal


def _make_signal(**kwargs) -> Signal:
    defaults = dict(
        blind_spot=None,
        invariant=None,
        retract=None,
        geometry_changed=False,
        next_query=None,
        done=False,
        falsification=None,
    )
    defaults.update(kwargs)
    return Signal(**defaults)


def _make_agent() -> TGSAgent:
    agent = TGSAgent(api_key="mock")
    agent.client = MagicMock()
    return agent


class TestDecideMode:

    def test_direct_when_done_and_clean(self):
        agent = _make_agent()
        signal = _make_signal(done=True)
        mode, reason = agent._decide_mode(signal)
        assert mode == "direct"
        assert "done" in reason

    def test_full_when_blind_spot(self):
        agent = _make_agent()
        signal = _make_signal(
            blind_spot="question framing hides subgroup effects",
            done=False,
        )
        mode, reason = agent._decide_mode(signal)
        assert mode == "full"
        assert "blind_spot" in reason

    def test_full_when_geometry_changed(self):
        agent = _make_agent()
        signal = _make_signal(
            geometry_changed=True,
            invariant="effect depends on dose",
            done=False,
        )
        mode, reason = agent._decide_mode(signal)
        assert mode == "full"

    def test_full_when_retract(self):
        agent = _make_agent()
        signal = _make_signal(
            retract="caffeine always helps",
            done=False,
        )
        mode, reason = agent._decide_mode(signal)
        assert mode == "full"

    def test_full_when_next_query(self):
        agent = _make_agent()
        signal = _make_signal(
            next_query="subgroup effects caffeine anxiety",
            done=False,
        )
        mode, reason = agent._decide_mode(signal)
        assert mode == "full"

    def test_light_when_some_signal_no_conflict(self):
        agent = _make_agent()
        # done=False but no specific strong signal
        signal = _make_signal(done=False)
        mode, reason = agent._decide_mode(signal)
        assert mode == "light"

    def test_direct_overridden_by_blind_spot(self):
        """done=True but blind_spot present → should be full, not direct."""
        agent = _make_agent()
        signal = _make_signal(
            done=True,
            blind_spot="framing excludes long-term effects",
        )
        mode, reason = agent._decide_mode(signal)
        assert mode == "full"

    def test_direct_overridden_by_geometry_change(self):
        """done=True but geometry changed → full."""
        agent = _make_agent()
        signal = _make_signal(
            done=True,
            geometry_changed=True,
            invariant="key invariant found",
        )
        mode, reason = agent._decide_mode(signal)
        assert mode == "full"


class TestTrivialGuard:
    """agent.ask() should bypass probe for obviously trivial queries."""

    def test_arithmetic_bypasses_probe(self):
        agent = _make_agent()

        # Patch _run_probe to detect if it was called
        probe_called = []
        original_probe = agent._run_probe
        def fake_probe(q):
            probe_called.append(q)
            return original_probe(q)
        agent._run_probe = fake_probe

        # Patch _answer_direct to avoid actual LLM call
        agent._answer_direct = lambda q: "42"

        result = agent.ask("6 * 7")
        assert result == "42"
        assert len(probe_called) == 0, "Probe should not be called for arithmetic"

    def test_open_question_calls_probe(self):
        agent = _make_agent()

        probe_called = []

        # Mock _run_probe
        from tgs.agent import ProbeResult
        mock_signal = _make_signal(done=True)
        mock_probe_result = ProbeResult(
            pages=[],
            signal=mock_signal,
            mode="direct",
            reason="mock",
        )

        agent._run_probe = lambda q: (probe_called.append(q), mock_probe_result)[1]
        agent._answer_direct = lambda q: "mock answer"

        agent.ask("does social media cause depression?")
        assert len(probe_called) == 1
