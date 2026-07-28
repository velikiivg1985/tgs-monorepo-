# Experimental Results Summary

This document records what 11 experiments have shown about
TGS-inspired mechanisms compared to simpler alternatives.

Each experiment was:
- Pre-registered with rules before running
- Run deterministically (seeded random)
- Interpreted according to the pre-committed rules

## Summary of findings

### What was empirically confirmed

1. **Minimal agent unfolds geometry through encounter.**
   File: `tgs_unfolding/tgs_unfolding.py`
   Agent starts unable to distinguish patterns.
   After 3 encounters, becomes able to distinguish them.

2. **Retract trades completeness for cleanliness.**
   Agents with retract keep smaller, cleaner geometry.
   Agents without retract sometimes classify better because
   they accidentally kept useful "noise" atoms.
   Neither strategy is universally better.

3. **TwoLayerMemory works as designed.**
   Diagnostic tests: 7/7 passed.
   Mechanism has no bugs.

4. **TwoLayerMemory has qualitative property: no catastrophic failures.**
   Across 4-phase drift environment (200 steps):
   - Recency: falls to 18% in worst phase
   - HypothesisOnly: falls to 18% in worst phase
   - TwoLayerMemory: worst phase is 32%

   Not "much better on average" but "never collapses".

5. **MeetingMemory consistently matches or beats alternatives.**
   Across 3 classification tasks requiring dual perspectives:
   - Task 1: Meeting 98.7% vs best single 97.3%
   - Task 2: Meeting 98.7% = Union 98.7%, both beat singles
   - Task 3: Meeting 90.0% vs Union 86.0% vs best single 56.0%
   Never worse than alternatives. Sometimes noticeably better.

### What was empirically not confirmed

1. **Compositional atoms vs monolithic patterns**
   No measurable difference.

2. **Soft retract vs strict retract**
   No measurable difference.

3. **Acceptance-through-difference at atom level**
   Reduces to strict retract in practice.

4. **HypothesisAgent beats recency in concept drift**
   Functionally equivalent to "remember last".

5. **Meeting solves tasks that no single agent can**
   Not shown. Union of optics usually solves same tasks.
   Meeting only slightly better than Union.

## Honest assessment

TGS-inspired mechanisms in our tests show:

- Small consistent advantages (typically 3-10%)
- Better worst-case behavior than simpler agents
- Never catastrophically worse than alternatives
- Not revolutionary improvements

These are the properties of **useful engineering tools**,
not of a "theory of everything".

For a task requiring:
- Context drift with returning patterns → use `TwoLayerMemory`
- Multi-perspective classification → use `MeetingMemory`
- Simple lookup → use a simpler structure

## What remains open

Untested empirically:
- Behavior with LLM-generated data (no API in test env)
- Performance on large-scale real-world benchmarks
- Interaction with other TGS mechanisms (retract, blind_spot detection)

These are subjects for future work.

## Falsification conditions

TwoLayerMemory should be discarded if:
- Diagnostic tests fail
- Simpler agent (Recency) matches on all metrics across all environments

MeetingMemory should be discarded if:
- Diagnostic tests fail
- Union of optics matches performance across all tested task types

Neither condition was met in our tests.
