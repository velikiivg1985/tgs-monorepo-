# TGS Search Agent

A self-correcting web agent built on three procedures.

## The procedures
1. Do not resolve contradictions — hold them.
2. Show the structure of the conflict, not a conclusion.
3. Name the condition under which you are wrong.

## Adaptive Routing (Gate Verdict)
TGS is not applied blindly. Before execution, the agent classifies the task:
- **Direct:** Factual, closed queries. TGS is bypassed to prevent over-complication.
- **Light:** Narrow technical tasks. Provides a direct answer + 1 falsification condition.
- **Full:** Open, contested, or complex queries. Engages the full TGS self-correcting loop.

*This prevents "ritualistic depth" on simple tasks.*

## Install & Run
```bash
pip install -e .
export OPENAI_API_KEY=sk-...
python run.py "your question"
python run.py --solve "write X that does Y"
