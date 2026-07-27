
#### `search_agent/PHILOSOPHY.md`
```markdown
# TGS Search Agent: Philosophy

## One idea
A system encounters difference. Difference changes the system. The changed system can now encounter what it could not encounter before.

## Theoretical lineages — concrete connections

### Vygotsky → `agent.py` search loop
The zone of proximal development: what the agent cannot do alone, it can do through encounter with external sources. `search()` is the mediating tool. The agent's next step depends on what it found, not just what it already knows.

### Porshnev → `executor.py`
Real resistance produces real distinction. Reading about an error is not the same as encountering one. `run_python()` returns `ExecutionResult`. A `success=False` result is not filtered out — it becomes the `blind_spot` input to the next monitor cycle.

### Ilyenkov → `monitor.py` procedure 1
Contradiction is not a bug. It is the engine. Procedure 1 says "do not resolve contradictions." The monitor maps conflict structure instead of collapsing it.

### Maturana & Varela → `geometry.py`
The system continuously produces its own boundary of distinctions. `Geometry.current()` is the lens for the next search step. `Geometry.retract()` means the boundary reshapes.

### von Foerster → `monitor.py` blind_spot
The observer cannot see what its own frame excludes. The monitor prompt explicitly asks "what the current geometry cannot see" — not what is missing in general, but what is missing *because of how the agent looks*.

### AGM (Alchourrón, Gärdenfors, Makinson) → `geometry.py`
Belief revision: contraction (retract) and revision (add after retract). `retract()` is AGM contraction. Retracted invariants are logged — they are data.

computational appendix:
https://medium.com/@velikiivg/theory-of-geometric-self-unfolding-tgs-a-conceptual-framework-for-a-unified-structural-e24637a3c82b
