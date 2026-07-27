# llm_simulation

A simplified simulation layer for TGS ideas, sitting between the minimal core and the full agent.

## Core idea
Encounter → Transformation → New distinction → New encounter

## What this layer is for
* compare simple agents with different update rules;
* simulate changes in a distinction space;
* test whether new distinctions emerge through encounter;
* separate genuine unfolding from mere state change.

## What this is not
This is not the full `search_agent`. It does not need web access, a real LLM (can be mocked), or a full execution loop. It should be as small as possible while still showing whether a system can acquire a new distinction through experience.
