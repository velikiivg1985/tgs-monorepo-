"""TGS Task Router (Gate Verdict). Determines optimal execution mode based on query structure."""
from __future__ import annotations
import json
from openai import OpenAI
from typing import Literal

Mode = Literal["direct", "light", "full"]

_ROUTER_SYSTEM = """You are a Task Router. Classify the user's query into ONE of three modes:
"direct": Closed, factual, micro-technical. Single correct answer exists. TGS is harmful here.
"light": Narrow technical or moderately open. Requires code/API, clear success criteria.
"full": Open, contested, multi-causal, or requiring deep reframing. Full TGS cycle needed.

Output ONLY valid JSON:
{"mode": "direct" | "light" | "full", "reason": "One sentence explaining why."}"""

def classify_task(client: OpenAI, model: str, query: str) -> tuple[Mode, str]:
    try:
        response = client.chat.completions.create(
            model=model, 
            temperature=0.0, 
            max_tokens=150,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _ROUTER_SYSTEM}, 
                {"role": "user", "content": query}
            ]
        )
        data = json.loads(response.choices[0].message.content)
        mode = data.get("mode", "full")
        reason = data.get("reason", "")
        
        if mode not in ("direct", "light", "full"):
            return "full", "Fallback: invalid mode returned."
        return mode, reason
    except Exception:
        return "full", "Fallback: router error."
