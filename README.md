# TGS — Theory of Geometric Self-Unfolding

An experimental framework for exploring how systems discover, revise, and expand their own geometry through encounter with difference and resistance.

> **A system encounters difference.
> Difference changes the system.
> The changed system sees what it could not see before.**

This repository is an attempt to make that process executable.

TGS — Theory of Geometric Self-Unfolding — is not presented as a finished scientific theory, a theory of consciousness, or a proven model of reality.

It is an experimental framework.

The central question is:

> **What happens when a system is designed not only to find answers, but to discover the limits of the way it is currently looking?**

---

## The Core Idea

A system begins with a limited geometry: a set of distinctions, assumptions, concepts, and relations through which it interprets the world.

It encounters something that does not fit.

The encounter creates tension.

The system must then:

1. detect what it cannot currently see;
2. identify what remains invariant through conflict;
3. test its assumptions against reality;
4. retract distinctions that no longer hold;
5. expand or change its geometry;
6. continue from the transformed state.

The process can be expressed simply:

```text
encounter
    ↓
difference
    ↓
resistance
    ↓
recognition of a blind spot
    ↓
revision of geometry
    ↓
new possible distinctions
    ↓
new encounter
```

The geometry is not fixed.

It can grow.

It can also shrink.

A distinction that seemed fundamental may turn out to be an artifact of the observer's previous way of looking.

---

## Repository Structure

```text
tgs-monorepo/
│
├── README.md
├── .gitignore
├── pyproject.toml
│
├── tgs_unfolding/
│   ├── tgs_unfolding.py
│   └── README.md
│
├── llm_simulation/
│   ├── simulation.py
│   └── README.md
│
└── search_agent/
    ├── pyproject.toml
    ├── run.py
    ├── README.md
    ├── PHILOSOPHY.md
    │
    ├── tgs/
    │   ├── __init__.py
    │   ├── geometry.py
    │   ├── search.py
    │   ├── monitor.py
    │   ├── executor.py
    │   └── agent.py
    │
    ├── tests/
    │   ├── test_geometry.py
    │   └── test_executor.py
    │
    └── experiments/
        ├── compare.py
        └── vocab_test.py
```

---

## The Three Layers

The repository contains three different levels of the same idea.

### 1. `tgs_unfolding/`

The minimal mathematical and conceptual core.

This is the simplest expression of the unfolding process:

```text
state
  ↓
encounter
  ↓
difference
  ↓
transformation
  ↓
new state
```

The purpose of this layer is not to simulate intelligence.

It is to ask:

> **Can self-unfolding be represented as a minimal formal process?**

---

### 2. `llm_simulation/`

A controlled simulation.

This layer explores what happens when a language model is placed inside a simplified unfolding process.

The goal is not to claim that the model becomes conscious.

The goal is to test whether a system can:

* maintain a changing internal geometry;
* encounter contradictions;
* detect limitations in its current representation;
* revise previous distinctions;
* generate new questions from transformed states.

This is an experimental environment.

---

### 3. `search_agent/`

An operational architecture.

This is where the philosophy becomes an agent design.

The agent is organized around several distinct functions:

```text
search
  ↓
monitor
  ↓
geometry
  ↓
action
  ↓
resistance
  ↓
revision
  ↓
search again
```

The architecture separates:

| Component     | Function                                            |
| ------------- | --------------------------------------------------- |
| `search.py`   | Encounter with difference                           |
| `monitor.py`  | Questions about the limits of current understanding |
| `geometry.py` | Adding and retracting distinctions                  |
| `executor.py` | Encounter with real resistance                      |
| `agent.py`    | The self-correcting cycle                           |

The central loop is:

```text
question
    ↓
search
    ↓
monitor
    ↓
geometry changes
    ↓
search again through the new geometry
    ↓
synthesis
```

For execution:

```text
task
    ↓
understand
    ↓
write code
    ↓
run code
    ↓
real resistance
    ↓
monitor
    ↓
revise geometry
    ↓
fix
```

---

## The Four Questions

The search agent is built around four questions.

### 1. What can I not see?

The system attempts to identify blind spots created by its current way of looking.

```text
blind_spot
```

The important point is that a blind spot is not simply missing information.

It may be produced by the structure of the observer itself.

---

### 2. What holds despite conflict?

The system searches for invariants.

An invariant is not necessarily the answer.

It is a structure that continues to hold while other assumptions change.

```text
invariant
```

---

### 3. How has my way of looking changed?

The system compares its current geometry with its previous geometry.

```text
geometry_changed
```

A change in understanding is therefore not only the addition of information.

The structure of the space in which the system can think may have changed.

---

### 4. What step has not yet been verified by reality?

In execution, the system must encounter something that is not merely a description of resistance.

It must actually fail, produce an unexpected result, or encounter a constraint.

```text
next_action
```

The error is not noise.

It is information about the distance between the system's model and what actually happens.

---

## A Minimal Formalism

Let the current geometry of a system be:

```text
Dₜ
```

Initially:

```text
D₀ = ∅
```

After an encounter:

```text
Dₜ₊₁ = (Dₜ ∪ {new distinctions}) \ {retracted distinctions}
```

A search step can be represented as:

```text
search_step(question, Dₜ):

    encounter = search(question)

    blind = what_cannot_be_seen(encounter, Dₜ)

    invariant = what_holds(encounter)

    wrong = what_was_wrong(encounter, Dₜ)

    Dₜ₊₁ =
        (Dₜ ∪ {invariant})
        \ {wrong}

    if geometry_stable:
        synthesise(Dₜ₊₁)

    else:
        search_again(Dₜ₊₁)
```

An execution step:

```text
execute_step(task, code, Dₜ):

    result = run(code)

    resistance = result.error

    invariant = what_holds(result, Dₜ)

    wrong = what_was_wrong(result, Dₜ)

    Dₜ₊₁ =
        (Dₜ ∪ {invariant})
        \ {wrong}

    if task_complete:
        return result

    else:
        revise(code, Dₜ₊₁)
```

This is not intended to be a complete theory of cognition.

It is a minimal architecture for experimentation.

---

## Philosophical Background

The architecture emerged from a convergence of ideas across different traditions.

It draws inspiration from questions concerning:

* the observer and self-reference;
* contradiction and development;
* resistance as a source of information;
* autopoiesis and self-production;
* boundaries as sites of transformation;
* the expansion of the possible;
* the relationship between external interaction and internal capability.

The full philosophical and architectural background is described in:

**[`search_agent/PHILOSOPHY.md`](search_agent/PHILOSOPHY.md)**

The philosophy is not treated as a specification that the code must prove.

Instead:

> **The code is an experiment that can change the philosophy.**

If implementation contradicts the original idea, the contradiction is part of the experiment.

---

## What This Project Is Not

TGS does **not** claim to:

* create consciousness;
* create subjective experience;
* prove that artificial systems are alive;
* prove a metaphysical theory;
* replace science, philosophy, psychology, or computer science;
* produce unlimited novelty;
* provide a complete theory of intelligence.

The project is deliberately more modest.

It asks whether certain philosophical questions can be turned into executable mechanisms.

---

## Why Build It?

Many systems are designed to optimize within a predefined geometry.

They are given:

```text
a goal
a representation
a set of possible actions
```

They then search for the best solution inside that space.

TGS explores a different possibility:

> **What if the system must also be able to question the geometry of the space in which it is searching?**

The central problem is not only:

```text
What is the answer?
```

but also:

```text
What assumptions make this answer visible?
What remains invisible because of those assumptions?
What would have to change for a different answer to become possible?
```

---

## Status

This is an experimental and evolving repository.

The architecture is expected to change.

The concepts are expected to be challenged.

The implementation may reveal that some ideas are:

* useful;
* incomplete;
* redundant;
* impossible to operationalize;
* or simply wrong.

That is not a failure of the project.

The project is designed around the possibility that its own current geometry is incomplete.

---

## The Principle

The repository can be reduced to one principle:

> **A system does not unfold by accumulating answers alone. It unfolds when encounters change the space in which answers can exist.**

---

## License

MIT

---

## Final Note

This repository is not a finished answer.

It is a structure designed to encounter answers that may change it.

Everything here is provisional.

Including this README.
