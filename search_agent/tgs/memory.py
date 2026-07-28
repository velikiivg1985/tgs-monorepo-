"""
tgs/memory.py

Empirically-derived memory architectures for TGS agents.

Based on 11 experiments comparing TGS-inspired mechanisms
against simpler alternatives. Results summarized in:
  experiments/RESULTS.md

Two architectures are provided:

    TwoLayerMemory
        Combines fast (recency) and slow (hypothesis) layers.
        Never catastrophically fails.
        Small consistent advantage on drift-heavy tasks.

    MeetingMemory
        Two agents with different optics exchange through a medium.
        Solves classification tasks that require multiple perspectives.
        Consistent small advantage over union of separate optics.

Neither is a silver bullet. Both are documented tools
for specific classes of problems.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, Optional


# ══════════════════════════════════════════════════════════════════════════
# ATOM UTILITIES
# ══════════════════════════════════════════════════════════════════════════

def extract_equality_atoms(sequence: list) -> frozenset[str]:
    """
    Extract pairwise equality atoms from a sequence.
    None values are treated as unknown and skipped.
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
    """Check if atoms are compatible with a partial signal."""
    for atom in atoms:
        parts = atom.replace("eq_", "").split("=")
        i, j = int(parts[0]), int(parts[1])
        if i < len(partial) and j < len(partial):
            if partial[i] is not None and partial[j] is not None:
                if partial[i] != partial[j]:
                    return False
    return True


# ══════════════════════════════════════════════════════════════════════════
# HYPOTHESIS
# ══════════════════════════════════════════════════════════════════════════

@dataclass
class Hypothesis:
    """
    A structural hypothesis. Never deleted once formed.
    May 'sleep' when its context is absent, wake when it returns.
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


# ══════════════════════════════════════════════════════════════════════════
# TWO-LAYER MEMORY
# ══════════════════════════════════════════════════════════════════════════

class TwoLayerMemory:
    """
    Fast recency layer + slow hypothesis layer.

    Prediction priority:
        1. Recency, if compatible with signal
        2. Strongest compatible hypothesis
        3. Empty (honest unknown)

    Empirical properties (see experiments/RESULTS.md):
        - Never falls below ~30% on any phase in drift tests
        - Small consistent advantage over recency alone
        - No catastrophic failures where simpler agents collapse

    Not universally better. Justified only when task involves
    context drift with returning patterns.
    """

    SIMILARITY_THRESHOLD: float = 0.7

    def __init__(
        self,
        extractor: Callable[[list], frozenset[str]] = extract_equality_atoms,
        similarity_threshold: Optional[float] = None,
    ) -> None:
        self._extractor = extractor
        if similarity_threshold is not None:
            self.SIMILARITY_THRESHOLD = similarity_threshold
        self._step: int = 0
        self._recency: frozenset[str] = frozenset()
        self._hypotheses: list[Hypothesis] = []

    def predict(self, partial: list) -> frozenset[str]:
        if self._recency and atoms_compatible_with_partial(self._recency, partial):
            return self._recency
        compatible = [h for h in self._hypotheses if h.compatible_with(partial)]
        if not compatible:
            return frozenset()
        best = max(compatible, key=lambda h: (h.strength, h.last_active_at))
        return best.atoms

    def learn(self, sequence: list) -> bool:
        """Update both layers. Returns True if a new hypothesis was created."""
        self._step += 1
        atoms = self._extractor(sequence)
        self._recency = atoms
        if not atoms:
            return False
        matched = False
        for h in self._hypotheses:
            if h.overlap(atoms) >= self.SIMILARITY_THRESHOLD:
                h.strength += 1
                h.last_active_at = self._step
                matched = True
        if not matched:
            self._hypotheses.append(Hypothesis(
                atoms=atoms,
                strength=1,
                last_active_at=self._step,
                born_at=self._step,
            ))
            return True
        return False

    def recency(self) -> frozenset[str]:
        return self._recency

    def hypotheses(self) -> list[Hypothesis]:
        return list(self._hypotheses)

    def step(self) -> int:
        return self._step

    def summary(self) -> str:
        top = sorted(self._hypotheses, key=lambda h: -h.strength)[:3]
        lines = [f"  recency: {sorted(self._recency)}"]
        lines.append(f"  total hypotheses: {len(self._hypotheses)}")
        for i, h in enumerate(top):
            lines.append(
                f"  #{i+1} strength={h.strength} atoms={sorted(h.atoms)}"
            )
        return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════
# MEETING MEMORY
# ══════════════════════════════════════════════════════════════════════════

class MeetingMemory:
    """
    Two agents with different optics meet through a medium.

    Each optic sees the sequence differently.
    The medium stores joint patterns (optic_A_view, optic_B_view) -> class.
    Marginal memories (each optic alone -> class) serve as fallback.

    Prediction priority:
        1. Joint pattern in medium
        2. Combined vote from marginals

    Empirical properties (see experiments/RESULTS.md):
        - Never worse than best single optic
        - Never worse than union of optics
        - Small consistent advantage on tasks requiring both optics

    Justified when a task requires perspectives that no single
    optic captures alone.
    """

    def __init__(
        self,
        optic_a: Callable[[list], frozenset[str]],
        optic_b: Callable[[list], frozenset[str]],
    ) -> None:
        self._optic_a = optic_a
        self._optic_b = optic_b
        self._medium: dict = {}  # (sig_a, sig_b) -> {class: count}
        self._a_alone: dict = {}  # sig_a -> {class: count}
        self._b_alone: dict = {}  # sig_b -> {class: count}

    def learn(self, sequence: list, label: str) -> None:
        sa = self._optic_a(sequence)
        sb = self._optic_b(sequence)
        self._increment(self._medium, (sa, sb), label)
        self._increment(self._a_alone, sa, label)
        self._increment(self._b_alone, sb, label)

    def predict(self, sequence: list) -> str:
        sa = self._optic_a(sequence)
        sb = self._optic_b(sequence)
        key = (sa, sb)
        if key in self._medium:
            return self._most_common(self._medium[key])
        a_counts = self._a_alone.get(sa, {})
        b_counts = self._b_alone.get(sb, {})
        combined = {}
        for cls, cnt in a_counts.items():
            combined[cls] = combined.get(cls, 0) + cnt
        for cls, cnt in b_counts.items():
            combined[cls] = combined.get(cls, 0) + cnt
        if not combined:
            return "UNKNOWN"
        return self._most_common(combined)

    def medium_size(self) -> int:
        return len(self._medium)

    @staticmethod
    def _increment(store: dict, key, label: str) -> None:
        if key not in store:
            store[key] = {}
        store[key][label] = store[key].get(label, 0) + 1

    @staticmethod
    def _most_common(counts: dict) -> str:
        return max(counts.items(), key=lambda x: x[1])[0]
