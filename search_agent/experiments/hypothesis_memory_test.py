#!/usr/bin/env python3
"""
hypothesis_memory_test.py

Empirical test of TwoLayerMemory vs simpler alternatives.

This experiment reproduces the key finding from our research:

    - Recency wins in static environments
    - HypothesisAgent wins in complex environments
    - Neither wins overall
    - TwoLayerMemory should win in both

Environments:
    Phase 1 (1-50):   High variability, 4 structures mixed
    Phase 2 (51-100): Static, one structure dominates
    Phase 3 (101-150): Another structure dominates
    Phase 4 (151-200): Mixed again, old structures return

Agents:
    Recency        — remembers only last seen structure
    HypothesisOnly — hypothesis layer only (our original agent)
    TwoLayer       — recency + hypothesis (new architecture)

Falsification rule (pre-committed):
    TwoLayerMemory is NOT justified if:
    - Recency matches or beats it in total score
    - HypothesisOnly matches or beats it in total score
    Both simpler agents must lose for the architecture to be confirmed.

Run:
    python experiments/hypothesis_memory_test.py
"""
from __future__ import annotations

import random
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tgs.memory import TwoLayerMemory, extract_atoms, atoms_compatible_with_partial


# ── Simple agents for comparison ──────────────────────────────────────────────

class RecencyAgent:
    name = "Recency"

    def __init__(self):
        self._last = frozenset()

    def predict(self, partial):
        compatible = {
            a for a in self._last
            if _atom_ok(a, partial)
        }
        return frozenset(compatible)

    def learn(self, sequence):
        self._last = extract_atoms(sequence)


class HypothesisOnlyAgent:
    """Hypothesis layer without recency — our original HypothesisAgent."""
    name = "HypothesisOnly"

    SIMILARITY_THRESHOLD = 0.7

    def __init__(self):
        from tgs.memory import Hypothesis
        self._hypotheses = []
        self._step = 0
        self._Hypothesis = Hypothesis

    def predict(self, partial):
        compatible = [
            h for h in self._hypotheses
            if h.compatible_with(partial)
        ]
        if not compatible:
            return frozenset()
        best = max(compatible, key=lambda h: (h.strength, h.last_active_at))
        return best.atoms

    def learn(self, sequence):
        self._step += 1
        atoms = extract_atoms(sequence)
        if not atoms:
            return
        matched = False
        for h in self._hypotheses:
            if h.overlap(atoms) >= self.SIMILARITY_THRESHOLD:
                h.strength += 1
                h.last_active_at = self._step
                matched = True
        if not matched:
            self._hypotheses.append(self._Hypothesis(
                atoms=atoms,
                strength=1,
                last_active_at=self._step,
                born_at=self._step,
            ))


class TwoLayerAgent:
    name = "TwoLayerMemory"

    def __init__(self):
        self._memory = TwoLayerMemory()

    def predict(self, partial):
        return self._memory.predict(partial)

    def learn(self, sequence):
        self._memory.learn(sequence)

    def summary(self):
        return self._memory.summary()


def _atom_ok(atom: str, partial: list) -> bool:
    parts = atom.replace("eq_", "").split("=")
    i, j = int(parts[0]), int(parts[1])
    if i < len(partial) and j < len(partial):
        if partial[i] is not None and partial[j] is not None:
            return partial[i] == partial[j]
    return True


# ── Environment ────────────────────────────────────────────────────────────────

class PhaseEnvironment:
    """
    4 worlds with changing distributions across 4 phases.
    Partial signal shows 2 random positions.
    """

    WORLDS = {
        "ABAB": [0, 1, 0, 1],
        "AABB": [0, 0, 1, 1],
        "ABBA": [0, 1, 1, 0],
        "AAAB": [0, 0, 0, 1],
    }

    PHASES = {
        1: {"ABAB": 0.4, "AABB": 0.4, "ABBA": 0.1, "AAAB": 0.1},
        2: {"ABAB": 0.05, "AABB": 0.05, "ABBA": 0.85, "AAAB": 0.05},
        3: {"ABAB": 0.05, "AABB": 0.05, "ABBA": 0.05, "AAAB": 0.85},
        4: {"ABAB": 0.3, "AABB": 0.25, "ABBA": 0.25, "AAAB": 0.2},
    }

    PHASE_SIZE = 50

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)
        self.alphabet = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        self._step = 0

    def next(self):
        self._step += 1
        phase = min(4, (self._step - 1) // self.PHASE_SIZE + 1)
        dist  = self.PHASES[phase]

        world_name = self._sample(dist)
        pattern    = self.WORLDS[world_name]
        symbols    = {}
        for pos in sorted(set(pattern)):
            symbols[pos] = self.rng.choice(self.alphabet)

        full    = [symbols[p] for p in pattern]
        partial = self._make_partial(full)

        return partial, full, world_name, phase

    def _sample(self, dist: dict) -> str:
        r = self.rng.random()
        cum = 0.0
        for name, prob in dist.items():
            cum += prob
            if r < cum:
                return name
        return list(dist.keys())[-1]

    def _make_partial(self, full: list) -> list:
        n    = len(full)
        i, j = sorted(self.rng.sample(range(n), 2))
        partial = [None] * n
        partial[i] = full[i]
        partial[j] = full[j]
        return partial


# ── Runner ─────────────────────────────────────────────────────────────────────

def run(agent, total_steps: int = 200, seed: int = 42):
    env          = PhaseEnvironment(seed=seed)
    total        = 0
    by_phase     = {1: [0, 0], 2: [0, 0], 3: [0, 0], 4: [0, 0]}

    for _ in range(total_steps):
        partial, full, _, phase = env.next()
        predicted = agent.predict(partial)
        truth     = extract_atoms(full)

        ok = (predicted == truth)
        by_phase[phase][1] += 1
        if ok:
            total += 1
            by_phase[phase][0] += 1

        agent.learn(full)

    return total, by_phase


# ── Reporting ──────────────────────────────────────────────────────────────────

def report_table(results: dict, phase_results: dict, total_steps: int):
    print(f"\n{'─'*70}")
    print(
        f"  {'Agent':<22}"
        f"{'Ph1':>8}"
        f"{'Ph2':>8}"
        f"{'Ph3':>8}"
        f"{'Ph4':>8}"
        f"{'TOTAL':>10}"
    )
    print(f"  {'─'*65}")

    for name, total in results.items():
        phases = phase_results[name]
        row = f"  {name:<22}"
        for p in [1, 2, 3, 4]:
            c, t = phases[p]
            row += f"{str(c)+'/'+str(t):>8}"
        row += f"{str(total)+'/'+str(total_steps):>10}"
        print(row)


def verdict(results: dict, total_steps: int):
    two   = results.get("TwoLayerMemory", 0)
    rec   = results.get("Recency", 0)
    hyp   = results.get("HypothesisOnly", 0)
    best_simple = max(rec, hyp)

    margin = (two - best_simple) / total_steps * 100

    print(f"\n{'─'*70}")
    print("  VERDICT")
    print(f"{'─'*70}")
    print(f"  TwoLayerMemory vs best simple: {margin:+.1f}%")
    print()

    if two > rec and two > hyp and margin >= 10:
        print("  ✓ CONFIRMED: TwoLayerMemory beats both simpler agents.")
        print("  Two-layer architecture is justified by the data.")
        print()
        print("  This supports the empirical finding:")
        print("  Acceptance-as-coexistence requires both fast (recency)")
        print("  and slow (hypothesis) layers to outperform either alone.")
    elif two > best_simple:
        print(f"  ~ WEAK: TwoLayerMemory is ahead by only {margin:.1f}%.")
        print("  Architecture helps but not decisively.")
    elif two == best_simple:
        print("  = DRAW: TwoLayerMemory matches the simpler agent.")
        print("  The added complexity is not justified.")
    else:
        print("  ✗ FAILED: TwoLayerMemory does not beat simpler alternatives.")
        print("  Hypothesis layer adds noise rather than signal here.")

    print()
    print("  FALSIFICATION NOTE:")
    print("  If Recency alone matches TwoLayerMemory on your data,")
    print("  remove the hypothesis layer — it is not earning its complexity.")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    TOTAL_STEPS = 200
    SEED        = 42

    print("=" * 70)
    print("  HYPOTHESIS MEMORY TEST")
    print("  TwoLayerMemory vs Recency vs HypothesisOnly")
    print("=" * 70)
    print()
    print("  Pre-committed falsification rule:")
    print("  TwoLayerMemory must beat BOTH simpler agents by >10%")
    print("  to justify the added complexity.")

    agents = [
        RecencyAgent(),
        HypothesisOnlyAgent(),
        TwoLayerAgent(),
    ]

    results      = {}
    phase_results = {}

    for agent in agents:
        total, by_phase = run(agent, TOTAL_STEPS, SEED)
        results[agent.name]       = total
        phase_results[agent.name] = by_phase
        print(f"\n  [{agent.name}] done: {total}/{TOTAL_STEPS}")

    report_table(results, phase_results, TOTAL_STEPS)
    verdict(results, TOTAL_STEPS)

    # Show TwoLayer internal state
    two_agent = next(a for a in agents if isinstance(a, TwoLayerAgent))
    print(f"\n  TwoLayerMemory final state:")
    print(two_agent.summary())


if __name__ == "__main__":
    main()
