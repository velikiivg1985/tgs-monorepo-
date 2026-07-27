#!/usr/bin/env python3
"""TGS Multi-Agent Simulation v2 with Invariant Verification."""
from __future__ import annotations
import os
import json
import argparse
from dataclasses import dataclass, field
from typing import Optional, List, Dict
from openai import OpenAI

DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_BASE_URL = "https://api.openai.com/v1"
MAX_TOKENS = 300
TEMPERATURE = 0.7

AGENT_SYSTEMS: Dict[str, str] = {
    "Analyst": "You are Analyst. Basis: logic, falsifiability, evidence. Be brief (2-3 sentences). End with:\nRESISTS: yes/no\nHOLDS: [one word or 'none']",
    "Integrator": "You are Integrator. Basis: pattern, coherence, relation. Resist reductionism. Be brief. End with:\nRESISTS: yes/no\nHOLDS: [one word or 'none']",
    "Engineer": "You are Engineer. Basis: robustness, adaptation, failure-as-signal. Resist fragile theories. Be brief. End with:\nRESISTS: yes/no\nHOLDS: [one word or 'none']",
}

MONITOR_SYSTEM = """You are TGS Monitor. Detect the invariant across agents.
Output ONLY valid JSON:
{
  "shared_invariant": "one word/phrase or null",
  "geometry_expanded": true or false,
  "note": "one sentence explaining why"
}
Rules: shared_invariant is non-null only if >=2 agents agree. geometry_expanded is true only if genuinely new."""

@dataclass
class AgentResponse:
    name: str
    text: str
    resists: bool
    holds: Optional[str]

    @classmethod
    def parse(cls, name: str, raw: str) -> "AgentResponse":
        lines = raw.strip().splitlines()
        resists, holds, body_lines = False, None, []
        for line in lines:
            low = line.strip().lower()
            if low.startswith("resists:"): 
                resists = "yes" in low
            elif low.startswith("holds:"):
                val = line.split(":", 1)[1].strip().lower()
                holds = None if val in ("none", "", "null") else val
            else: 
                body_lines.append(line)
        # FIX: Restored proper newline join
        return cls(name=name, text="\n".join(body_lines).strip(), resists=resists, holds=holds)

    def describe(self) -> str:
        r = "RESIST" if self.resists else "ACCEPT"
        h = self.holds or "—"
        # FIX: Restored proper newline
        return f"[{self.name}] {r} | holds={h}\n  {self.text}"

    def as_dict(self) -> dict:
        return {"name": self.name, "resists": "yes" if self.resists else "no", "holds": self.holds or "none", "text": self.text}

@dataclass
class TGSAgentSim:
    name: str
    system: str
    geometry: list[str] = field(default_factory=list)

    def system_with_geometry(self) -> str:
        if not self.geometry: return self.system
        # FIX: Restored proper newline
        return self.system + f"\n\nYour current geometry: [{', '.join(self.geometry)}]"

class Simulation:
    def __init__(self, client: OpenAI, model: str):
        self.client = client
        self.model = model
        self.history: list[dict] = []
        self.geometry: list[str] = []
        self.agents = [TGSAgentSim(name=n, system=s, geometry=self.geometry) for n, s in AGENT_SYSTEMS.items()]

    def _call(self, system: str, user: str, temp: float = TEMPERATURE, max_t: int = MAX_TOKENS) -> str:
        resp = self.client.chat.completions.create(
            model=self.model, temperature=temp, max_tokens=max_t,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}]
        )
        return resp.choices[0].message.content.strip()

    def _verify_invariant(self, invariant: str) -> bool:
        if not self.history: return True
        last = self.history[-1]
        inv_words = {w.lower() for w in invariant.split() if len(w) > 3}
        if not inv_words: return True
        
        grounded_count = sum(
            1 for resp in last.get("responses", []) 
            if len(inv_words & {w.lower() for w in resp.get("text", "").split() if len(w) > 3}) / len(inv_words) >= 0.3
        )
        return grounded_count >= 2

    def step(self, claim: str, step_no: int):
        print(f"\n{'═'*70}\nSTEP {step_no}: {claim}\n{'═'*70}")
        responses: list[AgentResponse] = []
        for agent in self.agents:
            raw = self._call(system=agent.system_with_geometry(), user=claim)
            resp = AgentResponse.parse(agent.name, raw)
            responses.append(resp)
            print(f"\n{resp.describe()}")

        monitor_input = f"CLAIM: {claim}\n" + "\n".join(
            f"AGENT: {r.name}\nRESISTS: {'yes' if r.resists else 'no'}\nHOLDS: {r.holds or 'none'}\nTEXT: {r.text}\n" 
            for r in responses
        )
        monitor_raw = self._call(system=MONITOR_SYSTEM, user=monitor_input, temp=0.2, max_t=200)

        try:
            clean = monitor_raw.strip()
            if clean.startswith("```"):
                clean = clean.split("```")[1]
                if clean.startswith("json"): clean = clean[4:]
            data = json.loads(clean)
            shared = data.get("shared_invariant")
            expanded = bool(data.get("geometry_expanded", False))
            note = data.get("note", "")

            if shared and expanded:
                expanded = self._verify_invariant(shared)
                if not expanded: note = f"REJECTED: '{shared}' not grounded in agent responses"
        except (json.JSONDecodeError, KeyError):
            shared, expanded, note = None, False, f"parse error: {monitor_raw[:100]}"

        print(f"\n{'─'*70}\nTGS MONITOR\n  shared_invariant : {shared or 'none'}\n  geometry_expanded: {expanded}\n  note: {note}")

        if expanded and shared and shared not in self.geometry:
            self.geometry.append(shared)
            print(f"\n  → VERIFIED & learned: '{shared}'")
        elif shared and not expanded:
            print(f"\n  → NOT VERIFIED: '{shared}' — Monitor hallucination blocked")

        print(f"\n{'─'*70}\nCURRENT GEOMETRY: {self.geometry}")
        self.history.append({
            "step": step_no, "claim": claim, "responses": [r.as_dict() for r in responses],
            "shared_invariant": shared, "geometry_expanded": expanded, "monitor_note": note, "geometry": list(self.geometry)
        })

    def report(self):
        print(f"\n{'═'*70}\nFINAL REPORT\n{'═'*70}\n\nFINAL GEOMETRY: {self.geometry}\n\nINVARIANT HISTORY:")
        for r in self.history:
            marker = "◆" if r["geometry_expanded"] else "·"
            inv = r["shared_invariant"] or "—"
            print(f"  step {r['step']} {marker} {inv:<20} | {r['monitor_note']}")
        expanded = [r for r in self.history if r["geometry_expanded"]]
        print(f"\nSELF-UNFOLDING EVENTS: {len(expanded)}")
        if expanded:
            print(f"  D_{{t+1}} ⊃ D_t at steps: {', '.join(str(r['step']) for r in expanded)}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--claims", default=None)
    args = parser.parse_args()

    api_key = os.environ.get("OPENAI_API_KEY", "sk-placeholder")
    client = OpenAI(api_key=api_key, base_url=args.base_url)

    if args.claims:
        with open(args.claims) as f:
            claims = json.load(f)
    else:
        claims = [
            "A theory can be an optic rather than a test if it reveals connections that were previously invisible.",
            "When a model fails consistently at the edge cases, the failure is data about the geometry of the model, not the world.",
            "Two agents with incompatible bases can still share an invariant if neither destroys the other's frame."
        ]

    sim = Simulation(client=client, model=args.model)
    for i, claim in enumerate(claims, 1):
        sim.step(claim, i)
    sim.report()

if __name__ == "__main__":
    main()
