"""Tests for tgs/geometry.py — pure logic, no network, no LLM."""
from __future__ import annotations
import pytest
from tgs.geometry import Geometry, _normalize, _similar

class TestNormalize:
    def test_basic(self): assert "conflict" in _normalize("conflict is inevitable")
    def test_strips_short_words(self): assert _normalize("a is in the of") == set()
    def test_lowercases(self): assert "conflict" in _normalize("CONFLICT IS INEVITABLE")
    def test_empty(self): assert _normalize("") == set()

class TestSimilar:
    def test_identical(self): assert _similar("conflict is inevitable", "conflict is inevitable")
    def test_rephrasing(self): assert _similar("conflict is inevitable", "conflict is necessary and inevitable")
    def test_clearly_different(self): assert not _similar("observer cannot exit observation", "boundary is generative mechanism")
    def test_threshold(self):
        assert _similar("apple orange here", "apple orange there", threshold=0.1)
        assert not _similar("apple", "orange", threshold=0.99)

class TestGeometryAdd:
    def test_add_new(self):
        g = Geometry(); assert g.add("observer cannot exit observation") is True; assert g.size() == 1
    def test_add_duplicate_exact(self):
        g = Geometry(); g.add("observer cannot exit observation"); assert g.add("observer cannot exit observation") is False; assert g.size() == 
    def test_add_semantic_duplicate(self):
        g = Geometry(); g.add("conflict is inevitable"); assert g.add("conflict is necessary and inevitable") is False
    def test_add_genuinely_different(self):
        g = Geometry(); g.add("observer cannot exit observation"); assert g.add("boundary is the generative mechanism") is True; assert g.size() == 2
    def test_add_empty(self):
        g = Geometry(); assert g.add("") is False; assert g.add("   ") is False
    def test_add_strips_whitespace(self):
        g = Geometry(); g.add("  conflict is inevitable  "); assert g.current() == ["conflict is inevitable"]

class TestGeometryRetract:
    def test_retract_existing(self):
        g = Geometry(); g.add("conflict is inevitable"); assert g.retract("conflict is inevitable") is True; assert g.empty()
    def test_retract_by_similarity(self):
        g = Geometry(); g.add("conflict is inevitable"); assert g.retract("conflict is necessary and inevitable") is True; assert g.empty()
    def test_retract_unknown(self):
        g = Geometry(); g.add("observer cannot exit observation"); assert g.retract("something completely unrelated here") is False; assert g.size() == 1
    def test_retract_logs(self):
        g = Geometry(); g.add("conflict is inevitable"); g.retract("conflict is inevitable"); assert "conflict is inevitable" in g.retracted()
    def test_retract_preserves_others(self):
        g = Geometry(); g.add("conflict is inevitable"); g.add("boundary is the generative mechanism"); g.retract("conflict is inevitable"); assert g.size() == 1; assert "boundary is the generative mechanism" in g.current()
    def test_retract_empty(self):
        g = Geometry(); assert g.retract("") is False

class TestGeometryState:
    def test_initial_empty(self):
        g = Geometry(); assert g.empty(); assert g.size() == 0; assert g.current() == []; assert g.retracted() == []; assert not g.grew()
    def test_grew_after_add(self):
        g = Geometry(); g.add("conflict is inevitable"); assert g.grew()
    def test_history_tracks(self):
        g = Geometry(); g.add("first invariant here"); g.add("second invariant here"); h = g.history(); assert h[0] == []; assert h[1] == ["first invariant here"]
    def test_current_is_copy(self):
        g = Geometry(); g.add("conflict is inevitable"); g.current().append("mutation"); assert g.size() == 1
    def test_repr_empty(self): assert repr(Geometry()) == "D = ∅"
    def test_repr_nonempty(self):
        g = Geometry(); g.add("test"); assert "test" in repr(g)

class TestGeometryCycle:
    def test_retract_then_readd(self):
        g = Geometry(); g.add("conflict is inevitable"); g.retract("conflict is inevitable"); assert g.add("conflict is inevitable") is True
    def test_multiple_retractions_logged(self):
        g = Geometry()
        for _ in range(3): g.add("conflict is inevitable"); g.retract("conflict is inevitable")
        assert len(g.retracted()) == 3
