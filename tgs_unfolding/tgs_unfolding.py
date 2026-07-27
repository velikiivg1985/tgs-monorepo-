"""
tgs_unfolding.py

Minimal demonstration of self-unfolding.
One agent. One environment. One test.

The test: can the agent distinguish something
after encounters that it could not distinguish before?

∃x: x ∉ D_t ∧ x ∈ D_{t+1}

No LLM. No web search. No retry. Pure structure.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Geometry:
    """D_t — the set of distinctions available at time t."""
    _distinctions: set[str] = field(default_factory=lambda: {"same", "different"})

    def add(self, distinction: str) -> bool:
        if distinction in self._distinctions:
            return False
        self._distinctions.add(distinction)
        return True

    def can_distinguish(self, a: Any, b: Any) -> bool:
        raise NotImplementedError

    def size(self) -> int:
        return len(self._distinctions)

    def __contains__(self, item):
        return item in self._distinctions

    def __repr__(self):
        return f"D = {sorted(self._distinctions)}"


class StructuralGeometry(Geometry):
    def __init__(self):
        super().__init__()
        self._patterns: dict[str, list[tuple[int, int]]] = {}

    def learn_pattern(self, name: str, equal_pairs: list[tuple[int, int]]) -> bool:
        if name in self._patterns:
            return False
        self._patterns[name] = equal_pairs
        return self.add(name)

    def can_distinguish(self, seq1: list, seq2: list) -> bool:
        return self._signature(seq1) != self._signature(seq2)

    def _signature(self, seq: list) -> frozenset[str]:
        seen = set()
        for name, pairs in self._patterns.items():
            if all(i < len(seq) and j < len(seq) and seq[i] == seq[j] for i, j in pairs):
                seen.add(name)
        return frozenset(seen)


class PatternExtractor:
    """
    How the agent looks for patterns. This is the perceptual method.
    Self-unfolding means this itself can change (second-order unfolding).
    """
    def __init__(self):
        self._methods: list[str] = ["equality"]

    def extract(self, sequence: list) -> dict[str, list[tuple[int, int]]]:
        found = {}
        if "equality" in self._methods:
            pairs = self._find_equal_pairs(sequence)
            if pairs:
                found["_".join(f"{i}={j}" for i, j in pairs)] = pairs
        if "adjacency" in self._methods:
            pairs = self._find_adjacent_repeats(sequence)
            if pairs:
                found["adj_" + "_".join(f"{i}={j}" for i, j in pairs)] = pairs
        if "symmetry" in self._methods:
            pairs = self._find_mirror(sequence)
            if pairs:
                found["sym_" + "_".join(f"{i}={j}" for i, j in pairs)] = pairs
        return found

    def learn_method(self, method_name: str) -> bool:
        if method_name in self._methods:
            return False
        self._methods.append(method_name)
        return True

    @property
    def methods(self) -> list[str]:
        return list(self._methods)

    @staticmethod
    def _find_equal_pairs(seq: list) -> list[tuple[int, int]]:
        return [(i, j) for i in range(len(seq)) for j in range(i + 1, len(seq)) if seq[i] == seq[j]]

    @staticmethod
    def _find_adjacent_repeats(seq: list) -> list[tuple[int, int]]:
        return [(i, i + 1) for i in range(len(seq) - 1) if seq[i] == seq[i + 1]]

    @staticmethod
    def _find_mirror(seq: list) -> list[tuple[int, int]]:
        n = len(seq)
        return [(i, n - 1 - i) for i in range(n // 2) if seq[i] == seq[n - 1 - i]]


class MinimalAgent:
    THRESHOLD = 3

    def __init__(self):
        self.geometry = StructuralGeometry()
        self.extractor = PatternExtractor()
        self._counts: dict[str, int] = {}
        self._history: list[list] = []
        self._encounter_count: int = 0

    def encounter(self, sequence: list) -> bool:
        self._history.append(sequence)
        self._encounter_count += 1
        self._maybe_expand_perception()

        expanded = False
        patterns = self.extractor.extract(sequence)
        for pattern_name, pairs in patterns.items():
            self._counts[pattern_name] = self._counts.get(pattern_name, 0) + 1
            if self._counts[pattern_name] >= self.THRESHOLD:
                if self.geometry.learn_pattern(pattern_name, pairs):
                    expanded = True
        return expanded

    def _maybe_expand_perception(self):
        """
        Limitation: thresholds are hardcoded. True open-ended method discovery 
        would require meta-learning. The point here is to show the STRUCTURE 
        of second-order unfolding, not to solve it fully.
        """
        if self._encounter_count >= 5 and self.extractor.learn_method("adjacency"):
            print("  [second-order] acquired: adjacency detection")
        if self._encounter_count >= 8 and self.extractor.learn_method("symmetry"):
            print("  [second-order] acquired: symmetry detection")


class Environment:
    def __init__(self, pattern: list[int], alphabet: list):
        self.pattern = pattern
        self.alphabet = alphabet
        self._counter = 0

    def next(self) -> list:
        symbols = {}
        # Use sorted to guarantee deterministic order
        for pos in sorted(set(self.pattern)):
            symbols[pos] = self.alphabet[self._counter % len(self.alphabet)]
            self._counter += 1
        return [symbols[p] for p in self.pattern]


def run_experiment():
    print("=" * 50)
    print("SELF-UNFOLDING EXPERIMENT (two levels)")
    print("=" * 50)

    agent = MinimalAgent()
    env1 = Environment(pattern=[0, 1, 0, 1], alphabet=list("ABCDEFGHIJKLMNOPQRSTUVWXYZ"))
    env2 = Environment(pattern=[0, 1, 1, 0], alphabet=list("MNOPQRSTUVWXYZ"))

    abab, xyzw, abba = ['Q', 'P', 'Q', 'P'], ['X', 'Y', 'Z', 'W'], ['R', 'S', 'S', 'R']

    print(f"\n[BEFORE]")
    print(f"  Geometry  : {agent.geometry}")
    print(f"  Methods   : {agent.extractor.methods}")
    print(f"  ABAB≠XYZW : {agent.geometry.can_distinguish(abab, xyzw)}")
    print(f"  ABBA≠XYZW : {agent.geometry.can_distinguish(abba, xyzw)}")

    print(f"\n[ENCOUNTERS — ABAB environment]")
    for i in range(1, 6):
        seq = env1.next()
        unfolded = agent.encounter(seq)
        print(f"  {i}. {seq}{' ← UNFOLDING' if unfolded else ''}")

    print(f"\n[ENCOUNTERS — mirror environment]")
    for i in range(6, 12):
        seq = env2.next()
        unfolded = agent.encounter(seq)
        print(f"  {i}. {seq}{' ← UNFOLDING' if unfolded else ''}")

    print(f"\n[AFTER]")
    print(f"  Geometry  : {agent.geometry}")
    print(f"  Methods   : {agent.extractor.methods}")
    print(f"  ABAB≠XYZW : {agent.geometry.can_distinguish(abab, xyzw)}")
    print(f"  ABBA≠XYZW : {agent.geometry.can_distinguish(abba, xyzw)}")

    level1 = any(d not in {"same", "different"} for d in agent.geometry._distinctions)
    level2 = len(agent.extractor.methods) > 1

    print(f"\n[RESULT]")
    if level1: print("  ✓ Level 1: new patterns discovered (content)")
    if level2: print("  ✓ Level 2: new extraction methods acquired (perception)")
    if level1 and level2: print("  This is two-level self-unfolding.")
    return agent

if __name__ == "__main__":
    run_experiment()
