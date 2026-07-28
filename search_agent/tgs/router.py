"""
tgs/router.py

Triviality Guard — not a task classifier.

Previous version: classified queries into factual / narrow_technical / open_conflicted.
This version: only answers one question — is this obviously trivial?

Everything else is decided by the probe encounter in agent.py.

Why this matters:
    The old router was an external arbiter that decided whether TGS was needed.
    That is not TGS-consistent. TGS should decide its own mode
    through a real first encounter with the environment.

    This file now only guards against obvious waste:
    arithmetic, exact lookups, micro-code tasks.
    These do not need search. They do not need a monitor.
    They do not need geometry.

    Everything else goes to probe.

Theoretical basis:
    von Foerster — the system should observe itself observing.
    The old router was a pre-observation that bypassed observation.
    The probe is the system deciding from encounter, not from label.

Falsification:
    This guard is wrong if a query passes the trivial filter
    but actually has no useful signal in web sources —
    meaning the probe wastes a search call for nothing.
    In that case, the probe's done=True / no blind_spot
    will correctly route to direct mode anyway.
    So the cost of a false negative here is one extra search call.
    That is acceptable.
"""
from __future__ import annotations

import re


# ── Patterns ───────────────────────────────────────────────────────────────────

_ARITHMETIC = re.compile(
    r"^\s*-?\d+(\.\d+)?\s*[\+\-\*/x×÷]\s*-?\d+(\.\d+)?\s*$"
)

_FACTUAL_PREFIXES = [
    # English
    "what year",
    "when was",
    "when did",
    "who is",
    "who was",
    "who invented",
    "capital of",
    "how many days",
    "how many hours",
    "speed of light",
    "distance from",
    "release date of",
    "birthday of",
    "date of birth",
    "population of",
    # Russian
    "сколько будет",
    "сколько дней",
    "сколько часов",
    "в каком году",
    "когда был",
    "когда родился",
    "кто такой",
    "столица",
    "скорость света",
    "население",
    "дата рождения",
]

_MICRO_CODE_PATTERNS = [
    "write is_even",
    "write a function that reverses",
    "how to open a file in python",
    "hello world in",
    "print hello",
    "fibonacci sequence code",
    "swap two variables",
    "check if string is palindrome",
]


# ── Public API ─────────────────────────────────────────────────────────────────

def is_obviously_trivial(text: str) -> bool:
    """
    Returns True only for clearly trivial queries that require no search,
    no monitor, and no geometry update.

    Conservative by design: when in doubt, returns False.
    A false negative here costs one probe search call.
    A false positive here costs the user a shallow answer.
    False positives are worse. Err toward False.
    """
    if not text or not text.strip():
        return False

    t = text.strip()

    # Pure arithmetic
    if _ARITHMETIC.match(t):
        return True

    t_lower = t.lower()

    # Factual prefix patterns
    for pattern in _FACTUAL_PREFIXES:
        if t_lower.startswith(pattern):
            return True

    # Micro-code patterns
    for pattern in _MICRO_CODE_PATTERNS:
        if pattern in t_lower:
            return True

    return False


def triviality_reason(text: str) -> str | None:
    """
    If the query is trivially simple, return why.
    Used for logging only.
    """
    if not text or not text.strip():
        return None

    t = text.strip()

    if _ARITHMETIC.match(t):
        return "pure arithmetic"

    t_lower = t.lower()

    for pattern in _FACTUAL_PREFIXES:
        if t_lower.startswith(pattern):
            return f"factual prefix: '{pattern}'"

    for pattern in _MICRO_CODE_PATTERNS:
        if pattern in t_lower:
            return f"micro-code pattern: '{pattern}'"

    return None
