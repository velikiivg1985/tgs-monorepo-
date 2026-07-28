"""
TGS Search Agent v3.5

A self-correcting web agent built on three procedures:

    1. Do not resolve contradictions — hold them.
    2. Show the structure of the conflict, not a conclusion.
    3. Name the condition under which you are wrong.

Two modes:
    ask(question)  — epistemic: corrects errors of framing
    solve(task)    — pragmatic: corrects errors of execution

Routing (v3.4):
    Probe-based self-routing replaces external task classification.
    The system decides its own depth from the first real encounter.

Memory architectures (v3.5):
    Empirically-derived memory tools with documented properties.
    See experiments/RESULTS.md for the 11-experiment evaluation.

    TwoLayerMemory
        Fast recency + slow hypothesis layers.
        Never catastrophically fails.
        Use for context drift with returning patterns.

    MeetingMemory
        Two optics exchanging through a medium.
        Consistent small advantage on multi-perspective tasks.
        Use when task requires perspectives no single optic captures.

    Neither is a silver bullet. Both are documented engineering tools.

Empirically validated:
    The power of TGS is in the three procedures, not the vocabulary.
    See experiments/vocab_test.py.

    Memory architectures show small consistent advantages,
    never catastrophically worse than simpler alternatives.
    See experiments/RESULTS.md.
"""

from .agent import TGSAgent
from .memory import (
    TwoLayerMemory,
    MeetingMemory,
    Hypothesis,
    extract_equality_atoms,
    atoms_compatible_with_partial,
)

__version__ = "3.5.0"
__all__ = [
    "TGSAgent",
    "TwoLayerMemory",
    "MeetingMemory",
    "Hypothesis",
    "extract_equality_atoms",
    "atoms_compatible_with_partial",
]
