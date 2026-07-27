"""Geometry of distinctions — D_t. Can grow (add) and shrink (retract)."""
from __future__ import annotations
import re

def _normalize(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-zA-Z]+", text.lower()) if len(w) > 3}

def _similar(a: str, b: str, threshold: float = 0.6) -> bool:
    wa, wb = _normalize(a), _normalize(b)
    if not wa or not wb: return a.strip().lower() == b.strip().lower()
    return len(wa & wb) / len(wa | wb) >= threshold

class Geometry:
    def __init__(self, similarity_threshold: float = 0.6) -> None:
        self._invariants, self._history, self._retracted = [], [], []
        self._similarity_threshold = similarity_threshold

    def add(self, invariant: str) -> bool:
        if not invariant or not invariant.strip(): return False
        invariant = invariant.strip()
        if any(_similar(invariant, existing, self._similarity_threshold) for existing in self._invariants): return False
        self._history.append(list(self._invariants))
        self._invariants.append(invariant)
        return True

    def retract(self, invariant: str) -> bool:
        if not invariant or not invariant.strip(): return False
        for existing in list(self._invariants):
            if _similar(invariant, existing, self._similarity_threshold):
                self._history.append(list(self._invariants))
                self._invariants.remove(existing)
                self._retracted.append(existing)
                return True
        return False

    def current(self) -> list[str]: return list(self._invariants)
    def retracted(self) -> list[str]: return list(self._retracted)
    def history(self) -> list[list[str]]: return list(self._history)
    def grew(self) -> bool: return len(self._history) > 0
    def empty(self) -> bool: return len(self._invariants) == 0
    def size(self) -> int: return len(self._invariants)
    def __repr__(self) -> str: return "D = ∅" if self.empty() else "D = {" + ", ".join(self._invariants) + "}"
