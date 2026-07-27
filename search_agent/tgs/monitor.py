"""TGS Monitor — three procedures of self-knowing."""
from __future__ import annotations
import json, re, time
from dataclasses import dataclass
from typing import Optional
from openai import OpenAI

_SEARCH_SYSTEM = """You are TGS Monitor. Apply three procedures:
1. Do NOT resolve contradictions. Hold them. Map their structure.
2. The invariant is NOT the answer. It is what holds across ALL sources despite conflict.
3. The blind_spot is what the current geometry cannot see (structural absence).
Output ONLY valid JSON:
{"blind_spot": "..." or null, "invariant": "..." or null, "retract": "..." or null, "geometry_changed": true/false, "next_query": "..." or null, "done": true/false, "falsification": "..."}"""

_EXECUTION_SYSTEM = """You are TGS Monitor. Apply four procedures:
1. Do NOT dismiss execution errors as noise. The error IS the blind spot.
2. Find what holds despite the failure.
3. Name what existing belief the error falsifies (retract).
4. Ask: what step is not yet verified by reality?
Output ONLY valid JSON:
{"blind_spot": "..." or null, "invariant": "..." or null, "retract": "..." or null, "geometry_changed": true/false, "next_action": "fix_code"|"search_more"|"done", "corrected_code": "..." or null, "next_query": "..." or null, "done": true/false, "falsification": "..."}"""

@dataclass
class Signal:
    blind_spot: Optional[str]; invariant: Optional[str]; retract: Optional[str]
    geometry_changed: bool; next_query: Optional[str]; done: bool; falsification: Optional[str]

@dataclass
class ExecutionSignal:
    blind_spot: Optional[str]; invariant: Optional[str]; retract: Optional[str]
    geometry_changed: bool; next_action: str; corrected_code: Optional[str]
    next_query: Optional[str]; done: bool; falsification: Optional[str]

def ask(client: OpenAI, model: str, question: str, geometry: list[str], pages: list) -> Signal:
    pages_text = "\n\n".join(p.text() for p in pages) if pages else "No pages found."
    user = f"QUESTION: {question}\nGEOMETRY: {geometry or ['empty']}\nPAGES:\n{pages_text}"
    data = _call(client, model, _SEARCH_SYSTEM, user)
    return Signal(data.get("blind_spot"), data.get("invariant"), data.get("retract"), bool(data.get("geometry_changed", False)), data.get("next_query"), bool(data.get("done", False)), data.get("falsification"))

def ask_execution(client: OpenAI, model: str, task: str, geometry: list[str], code: str, result) -> ExecutionSignal:
    user = f"TASK: {task}\nGEOMETRY: {geometry or ['empty']}\nCODE:\n{code}\nRESULT:\n{result.as_text()}"
    data = _call(client, model, _EXECUTION_SYSTEM, user)
    return ExecutionSignal(data.get("blind_spot"), data.get("invariant"), data.get("retract"), bool(data.get("geometry_changed", False)), data.get("next_action", "done"), data.get("corrected_code"), data.get("next_query"), bool(data.get("done", False)), data.get("falsification"))

def _call(client: OpenAI, model: str, system: str, user: str, retries: int = 3, pause: float = 2.0) -> dict:
    for attempt in range(1, retries + 1):
        try:
            response = client.chat.completions.create(model=model, temperature=0.2, max_tokens=600, messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
            return _parse(response.choices[0].message.content.strip())
        except Exception as e:
            if attempt < retries:
                print(f"  [monitor] attempt {attempt} failed: {e}\n  [monitor] retrying in {pause}s ...")
                time.sleep(pause)
            else:
                print(f"  [monitor] all {retries} attempts failed: {e}")
    return {}

def _parse(raw: str) -> dict:
    if not raw: return {}
    for fn in (_direct, _extract_braces, _strip_markdown):
        result = fn(raw)
        if result: return result
    return {}

def _direct(raw: str) -> dict:
    try: return json.loads(raw)
    except json.JSONDecodeError: return {}

def _extract_braces(raw: str) -> dict:
    try:
        start, end = raw.find("{"), raw.rfind("}") + 1
        if start != -1 and end > start: return json.loads(raw[start:end])
    except json.JSONDecodeError: pass
    return {}

def _strip_markdown(raw: str) -> dict:
    try:
        clean = re.sub(r"```[a-z]*", "", raw).strip()
        start, end = clean.find("{"), clean.rfind("}") + 1
        if start != -1 and end > start: return json.loads(clean[start:end])
    except json.JSONDecodeError: pass
    return {}
