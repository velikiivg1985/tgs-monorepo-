"""
tgs/memory.py

Two-layer memory for TGS agents.

Discovered empirically through 9 experiments (see experiments/):

    Single-layer agents fail in one of two ways:
    - Accumulator: keeps everything, distinguishes nothing
    - Recency: adapts fast, but loses history
    - StrictTGS: clean geometry, but misses what it discarded

    The key finding:
    HypothesisAgent outperforms in complex phases (high variability).
    Recency outperforms in static phases (one dominant structure).

    Neither wins overall.

    Solution: hold both layers simultaneously.
    Use recency as fast adapter.
    Use hypotheses as slow memory of what was and may return.

    When signal arrives:
    1. Check recency layer — is it compatible?
    2. Check hypothesis layer — is there a stronger compatible structure?
    3. If both compatible — recency wins (faster, more current).
    4. If only hypothesis compatible — use it (recency doesn't help here).
    5. If neither — return empty (honest unknown).

This is the operational form of "acceptance through difference":
not choosing between past and present,
but holding both until the signal resolves the choice.

Theoretical basis:
    Experiments in experiments/toy_unfolding_experiment_v3.py
    Concept drift benchmark (experiments/hypothesis_memory_test.py)
    See PHILOSOPHY.md: "acceptance as coexistence of competing hypotheses"

Falsification condition:
    This layer is wrong if a simpler architecture (Recency alone)
    consistently matches or beats TwoLayerMemory across diverse tasks.
    Run experiments/hypothesis_memory_test.py to check.
"""
from __future__ import annotations

from dataclasses import dataclass, field


# ── Atom extractor ─────────────────────────────────────────────────────────────

def extract_atoms(sequence: list) -> frozenset[str]:
    """
    Extract pairwise equality atoms from a sequence.
    None values are treated as unknown — skipped.

    Example:
        ['A', 'B', 'A', 'B'] -> {'eq_0=2', 'eq_1=3'}
        ['A', None, 'A', None] -> {'eq_0=2'}
    """
    atoms = set()
    n = len(sequence)
    for i in range(n):
        for j in range(i + 1, n):
            if sequence[i] is not None and sequence[j] is not None:
                if sequence[i] == sequence[j]:
                    atoms.add(f"eq_{i}={j}")
    return frozenset(atoms)


def atoms_compatible_with_partial(
    atoms: frozenset[str],
    partial: list,
) -> bool:
    """
    Check if a set of atoms is compatible with a partial signal.
    Compatible = no direct contradiction in visible positions.

    Example:
        atoms = {'eq_0=2', 'eq_1=3'}
        partial = ['A', 'B', None, None]
        → compatible (no contradiction visible)

        atoms = {'eq_0=1'}
        partial = ['A', 'B', None, None]
        → incompatible (A ≠ B, but eq_0=1 requires them equal)
    """
    for atom in atoms:
        parts = atom.replace("eq_", "").split("=")
        i, j = int(parts[0]), int(parts[1])
        if i < len(partial) and j < len(partial):
            if partial[i] is not None and partial[j] is not None:
                if partial[i] != partial[j]:
                    return False
    return True


# ── Hypothesis ─────────────────────────────────────────────────────────────────

@dataclass
class Hypothesis:
    """
    A structural hypothesis — one coherent way of seeing.

    Not a collection of atoms. A living structure with:
    - its own atoms (what it sees)
    - its strength (how often confirmed)
    - its age (when last active)
    - its origin (when born)

    A hypothesis is never deleted.
    It may sleep for a long time and wake up when its
    context returns. This is the operational meaning of
    "acceptance as coexistence".
    """
    atoms          : frozenset[str]
    strength       : int = 1
    last_active_at : int = 0
    born_at        : int = 0

    def compatible_with(self, partial: list) -> bool:
        return atoms_compatible_with_partial(self.atoms, partial)

    def overlap(self, other: frozenset[str]) -> float:
        if not self.atoms and not other:
            return 1.0
        union = self.atoms | other
        inter = self.atoms & other
        return len(inter) / len(union) if union else 0.0

    def __repr__(self) -> str:
        return (
            f"Hypothesis(strength={self.strength}, "
            f"last_active={self.last_active_at}, "
            f"atoms={sorted(self.atoms)})"
        )


# ── Two-layer memory ───────────────────────────────────────────────────────────

class TwoLayerMemory:
    """
    The empirically derived memory architecture for TGS agents.

    Layer 1 (Fast): Recency
        Always tracks the most recent structure.
        Adapts in one step.
        Good for stable, repeating environments.

    Layer 2 (Slow): Hypotheses
        Accumulates structural hypotheses over time.
        Each hypothesis persists — never deleted.
        Good for complex, changing environments.

    Prediction:
        Given a partial signal, try recency first.
        If recency is not compatible, fall back to
        the strongest compatible hypothesis.
        If neither, return empty (honest unknown).

    This dual strategy is why HypothesisAgent outperformed
    Recency in complex phases but underperformed in static ones:
    it had the slow layer but lacked the fast layer.

    With both layers, the agent should perform well in both regimes.

    Falsification:
        If Recency alone consistently matches TwoLayerMemory,
        then the slow layer adds nothing and should be removed.
        Run hypothesis_memory_test.py to verify.
    """

    SIMILARITY_THRESHOLD: float = 0.7

    def __init__(self) -> None:
        self._step       : int               = 0
        self._recency    : frozenset[str]    = frozenset()
        self._hypotheses : list[Hypothesis]  = []

    # ── Public: predict ────────────────────────────────────────────────────────

    def predict(self, partial: list) -> frozenset[str]:
        """
        Predict the full structure given a partial signal.

        Priority:
        1. Recency — if compatible, use it (fast, current).
        2. Strongest compatible hypothesis — if recency fails.
        3. Empty — if nothing is compatible (honest unknown).
        """
        # Fast layer: recency
        if self._recency and atoms_compatible_with_partial(
            self._recency, partial
        ):
            return self._recency

        # Slow layer: best compatible hypothesis
        compatible = [
            h for h in self._hypotheses
            if h.compatible_with(partial)
        ]
        if not compatible:
            return frozenset()

        best = max(compatible, key=lambda h: (h.strength, h.last_active_at))
        return best.atoms

    # ── Public: learn ──────────────────────────────────────────────────────────

    def learn(self, sequence: list) -> bool:
        """
        Update both layers from a full sequence.

        Returns True if a new hypothesis was created
        (i.e., geometry expanded at the hypothesis level).
        """
        self._step += 1
        atoms = extract_atoms(sequence)

        # Update fast layer
        self._recency = atoms

        # Update slow layer
        return self._update_hypotheses(atoms)

    # ── Public: inspect ────────────────────────────────────────────────────────

    def hypotheses(self) -> list[Hypothesis]:
        return list(self._hypotheses)

    def recency(self) -> frozenset[str]:
        return self._recency

    def step(self) -> int:
        return self._step

    def summary(self) -> str:
        top = sorted(
            self._hypotheses,
            key=lambda h: -h.strength
        )[:3]
        parts = [f"  recency: {sorted(self._recency)}"]
        for i, h in enumerate(top):
            parts.append(
                f"  hyp #{i+1}: strength={h.strength} "
                f"atoms={sorted(h.atoms)}"
            )
        return "\n".join(parts)

    # ── Internal ───────────────────────────────────────────────────────────────

    def _update_hypotheses(self, atoms: frozenset[str]) -> bool:
        """
        Update hypothesis layer.
        If atoms overlap with existing hypothesis — strengthen it.
        If no match — create new hypothesis.
        Returns True if new hypothesis was created.
        """
        if not atoms:
            return False

        matched_any = False
        for hyp in self._hypotheses:
            if hyp.overlap(atoms) >= self.SIMILARITY_THRESHOLD:
                hyp.strength += 1
                hyp.last_active_at = self._step
                matched_any = True

        if not matched_any:
            self._hypotheses.append(Hypothesis(
                atoms=atoms,
                strength=1,
                last_active_at=self._step,
                born_at=self._step,
            ))
            return True

        return False
