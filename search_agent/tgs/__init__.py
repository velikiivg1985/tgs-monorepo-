"""
TGS Search Agent v3.4

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

Empirically validated:
    The power of TGS is in the three procedures, not the vocabulary.
    See experiments/vocab_test.py.
"""

from .agent import TGSAgent

__version__ = "3.4.0"
__all__ = ["TGSAgent"]

from .memory import TwoLayerMemory, extract_atoms

__version__ = "3.5.0"
__all__ = ["TGSAgent", "TwoLayerMemory", "extract_atoms"]
