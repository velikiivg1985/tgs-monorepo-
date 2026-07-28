"""
Diagnostic tests for tgs/memory.py

These tests verify mechanisms work as designed.
They do NOT test whether the mechanisms give practical advantage.
For that, see experiments/hypothesis_memory_test.py.
"""
from __future__ import annotations
import pytest

from tgs.memory import (
    TwoLayerMemory,
    MeetingMemory,
    Hypothesis,
    extract_equality_atoms,
    atoms_compatible_with_partial,
)


# ── extract_equality_atoms ────────────────────────────────────────────────

class TestExtractAtoms:
    def test_abab_pattern(self):
        assert extract_equality_atoms(['A', 'B', 'A', 'B']) == \
            frozenset({"eq_0=2", "eq_1=3"})

    def test_all_different(self):
        assert extract_equality_atoms(['A', 'B', 'C', 'D']) == frozenset()

    def test_all_same(self):
        result = extract_equality_atoms(['A', 'A', 'A', 'A'])
        expected = frozenset({
            "eq_0=1", "eq_0=2", "eq_0=3",
            "eq_1=2", "eq_1=3", "eq_2=3",
        })
        assert result == expected

    def test_none_skipped(self):
        assert extract_equality_atoms(['A', None, 'A', None]) == \
            frozenset({"eq_0=2"})


# ── atoms_compatible_with_partial ────────────────────────────────────────

class TestCompatibility:
    def test_no_contradiction_compatible(self):
        atoms = frozenset({"eq_0=2"})
        assert atoms_compatible_with_partial(atoms, ['A', 'B', 'A', 'B'])

    def test_direct_contradiction_incompatible(self):
        atoms = frozenset({"eq_0=1"})
        assert not atoms_compatible_with_partial(atoms, ['A', 'B', None, None])

    def test_unknown_positions_compatible(self):
        atoms = frozenset({"eq_2=3"})
        assert atoms_compatible_with_partial(atoms, ['A', 'B', None, None])


# ── TwoLayerMemory ────────────────────────────────────────────────────────

class TestTwoLayerMemory:
    def test_recency_updates_each_step(self):
        m = TwoLayerMemory()
        m.learn(['A', 'B', 'A', 'B'])
        assert m.recency() == frozenset({"eq_0=2", "eq_1=3"})
        m.learn(['A', 'B', 'B', 'A'])
        assert m.recency() == frozenset({"eq_0=3", "eq_1=2"})

    def test_distinct_structures_create_hypotheses(self):
        m = TwoLayerMemory()
        m.learn(['A', 'B', 'A', 'B'])
        m.learn(['A', 'B', 'B', 'A'])
        m.learn(['A', 'A', 'B', 'B'])
        assert len(m.hypotheses()) == 3

    def test_same_structure_strengthens(self):
        m = TwoLayerMemory()
        m.learn(['A', 'B', 'A', 'B'])
        m.learn(['C', 'D', 'C', 'D'])
        assert len(m.hypotheses()) == 1
        assert m.hypotheses()[0].strength == 2

    def test_recency_wins_when_compatible(self):
        m = TwoLayerMemory()
        for _ in range(5):
            m.learn(['A', 'B', 'A', 'B'])
        m.learn(['A', 'B', 'B', 'A'])
        pred = m.predict(['A', 'B', None, 'A'])
        assert pred == frozenset({"eq_0=3", "eq_1=2"})

    def test_hypothesis_fallback_when_recency_fails(self):
        m = TwoLayerMemory()
        for _ in range(5):
            m.learn(['A', 'B', 'A', 'B'])
        m.learn(['C', 'C', 'D', 'D'])
        pred = m.predict(['A', 'B', 'A', None])
        assert pred == frozenset({"eq_0=2", "eq_1=3"})

    def test_sleeping_hypothesis_survives(self):
        m = TwoLayerMemory()
        m.learn(['A', 'B', 'A', 'B'])
        for _ in range(20):
            m.learn(['X', 'Y', 'Y', 'X'])
        abab_atoms = frozenset({"eq_0=2", "eq_1=3"})
        assert any(h.atoms == abab_atoms for h in m.hypotheses())
        pred = m.predict(['A', 'B', 'A', 'B'])
        assert pred == abab_atoms

    def test_empty_prediction_when_empty(self):
        m = TwoLayerMemory()
        assert m.predict(['A', 'B', 'C', 'D']) == frozenset()

    def test_no_atoms_from_all_different(self):
        m = TwoLayerMemory()
        m.learn(['A', 'B', 'C', 'D'])
        assert m.recency() == frozenset()
        assert len(m.hypotheses()) == 0


# ── MeetingMemory ─────────────────────────────────────────────────────────

def _equality_optic(seq):
    return extract_equality_atoms(seq)


def _length_optic(seq):
    """Simple secondary optic for testing."""
    return frozenset({f"len_{len(seq)}"})


class TestMeetingMemory:
    def test_joint_pattern_stored(self):
        m = MeetingMemory(_equality_optic, _length_optic)
        m.learn(['A', 'B', 'A', 'B'], "class_1")
        assert m.medium_size() == 1

    def test_prediction_from_joint(self):
        m = MeetingMemory(_equality_optic, _length_optic)
        for _ in range(3):
            m.learn(['A', 'B', 'A', 'B'], "ABAB")
        assert m.predict(['C', 'D', 'C', 'D']) == "ABAB"

    def test_fallback_to_marginals(self):
        """When joint pattern is unseen, fall back to marginals."""
        m = MeetingMemory(_equality_optic, _length_optic)
        for _ in range(3):
            m.learn(['A', 'B', 'A', 'B'], "ABAB")
        # New length, unseen joint, but eq_optic knows this pattern
        m.learn(['E', 'F', 'E', 'F', 'X'], "OTHER")
        # Predict for length=4 with same equality pattern
        # marginal from eq_optic should still work
        result = m.predict(['A', 'B', 'A', 'B'])
        assert result in {"ABAB", "OTHER"}

    def test_unknown_when_no_data(self):
        m = MeetingMemory(_equality_optic, _length_optic)
        assert m.predict(['A', 'B', 'C', 'D']) == "UNKNOWN"
