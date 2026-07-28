"""
Tests for tgs/router.py — triviality guard.
"""
from __future__ import annotations
import pytest
from tgs.router import is_obviously_trivial, triviality_reason


class TestObviouslyTrivial:

    # arithmetic
    def test_arithmetic_simple(self):
        assert is_obviously_trivial("17 * 19") is True

    def test_arithmetic_with_spaces(self):
        assert is_obviously_trivial("  3 + 4  ") is True

    def test_arithmetic_division(self):
        assert is_obviously_trivial("100 / 4") is True

    def test_arithmetic_float(self):
        assert is_obviously_trivial("3.14 * 2") is True

    # factual prefixes
    def test_factual_what_year(self):
        assert is_obviously_trivial("what year was Python released") is True

    def test_factual_capital(self):
        assert is_obviously_trivial("capital of France") is True

    def test_factual_who_is(self):
        assert is_obviously_trivial("who is Alan Turing") is True

    def test_factual_russian(self):
        assert is_obviously_trivial("сколько будет 5 плюс 3") is True

    def test_factual_russian_capital(self):
        assert is_obviously_trivial("столица России") is True

    # micro code
    def test_micro_code_is_even(self):
        assert is_obviously_trivial("write is_even function") is True

    def test_micro_code_hello(self):
        assert is_obviously_trivial("hello world in python") is True

    # non-trivial — should return False
    def test_not_trivial_complex_question(self):
        assert is_obviously_trivial(
            "does social media cause depression?"
        ) is False

    def test_not_trivial_philosophy(self):
        assert is_obviously_trivial(
            "what is the relationship between consciousness and information?"
        ) is False

    def test_not_trivial_code_complex(self):
        assert is_obviously_trivial(
            "write a function that sorts a graph topologically and handles cycles"
        ) is False

    def test_not_trivial_empty(self):
        assert is_obviously_trivial("") is False

    def test_not_trivial_vague(self):
        assert is_obviously_trivial("tell me something") is False


class TestTrivialityReason:
    def test_arithmetic_reason(self):
        assert triviality_reason("17 * 19") == "pure arithmetic"

    def test_factual_reason(self):
        r = triviality_reason("what year was Python released")
        assert r is not None
        assert "factual prefix" in r

    def test_non_trivial_none(self):
        assert triviality_reason("does social media cause depression?") is None
