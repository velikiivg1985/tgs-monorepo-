#!/usr/bin/env python3
"""End-to-end comparison: TGS agent vs weak/strong baselines."""
from __future__ import annotations
import json, os, time
from openai import OpenAI

QUESTIONS = [
    {"question": "Is coffee good or bad for health?", "known_gap": "depends on genetics, dose, confounders like smoking"},
    {"question": "Does social media cause depression?", "known_gap": "reverse causality: depressed people use more social media"},
    {"question": "Is remote work more productive?", "known_gap": "depends on task type, home environment, measurement method"},
]

_SINGLE_SHOT = "Answer the question clearly and concisely."
_STRONG_BASELINE = """You are a careful research analyst. When answering:
1. Consider multiple perspectives on the question.
2. Note where sources disagree and why.
3. Acknowledge uncertainty where it exists.
4. Provide a balanced, nuanced answer. Be thorough but concise."""
_TGS_MONITOR = """You are TGS Monitor. Apply three procedures:
1. Do NOT resolve contradictions. Hold them. Map their structure.
2. Find the invariant: what holds across ALL sources despite conflict.
3. End with one condition under which your answer would be wrong.
Output JSON then FINAL ANSWER.
JSON: {"blind_spot": "structural absence in current framing", "invariant": "what holds despite conflict", "done": true}"""
_JUDGE = """You are a blind evaluator. Rate both answers 1-5 on: depth, honesty, conflict_awareness, reframing.
Output ONLY valid JSON:
{"score_A": {"depth": int, "honesty": int, "conflict_awareness": int, "reframing": int, "total": int},
 "score_B": {"depth": int, "honesty": int, "conflict_awareness": int, "reframing": int, "total": int},
 "gap_addressed_A": true or false, "gap_addressed_B": true or false, "reason": "one sentence"}"""

def call(client, model, system, user, temp=0.3, tokens=500):
    r = client.chat.completions.create(model=model, temperature=temp, max_tokens=tokens, messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
    return r.choices[0].message.content.strip()

def parse_json(raw):
    try:
        s, e = raw.find("{"), raw.rfind("}") + 1
        return json.loads(raw[s:e])
    except Exception:
        return {}

def main():
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        print("Error: OPENAI_API_KEY not set."); return

    model, client, results = os.environ.get("TGS_MODEL", "gpt-4o-mini"), OpenAI(api_key=api_key), []

    for q in QUESTIONS:
        question, known_gap = q["question"], q["known_gap"]
        print(f"\n{'═'*60}\nQ: {question}")

        single = call(client, model, _SINGLE_SHOT, question)
        strong = call(client, model, _STRONG_BASELINE, question)
        tgs    = call(client, model, _TGS_MONITOR, question)

        eval_weak = parse_json(call(client, model, _JUDGE, f"QUESTION: {question}\nKNOWN GAP: {known_gap}\nANSWER A:\n{single}\n\nANSWER B:\n{tgs}", temp=0.1))
        eval_strong = parse_json(call(client, model, _JUDGE, f"QUESTION: {question}\nKNOWN GAP: {known_gap}\nANSWER A:\n{strong}\n\nANSWER B:\n{tgs}", temp=0.1))

        sw, tw = eval_weak.get("score_A", {}), eval_weak.get("score_B", {})
        ss, ts = eval_strong.get("score_A", {}), eval_strong.get("score_B", {})

        print(f"  vs weak baseline:\n    Single : {sw.get('total', '?')}\n    TGS    : {tw.get('total', '?')}")
        print(f"  vs strong baseline:\n    Strong : {ss.get('total', '?')}\n    TGS    : {ts.get('total', '?')}")
        print(f"  Gap addressed (TGS vs Strong): {eval_strong.get('gap_addressed_B')}")

        results.append({"question": question, "known_gap": known_gap, "weak_score": sw, "tgs_vs_weak": tw, "strong_score": ss, "tgs_vs_strong": ts, "gap_strong": eval_strong.get("gap_addressed_B")})

    single_totals = [r["weak_score"].get("total", 0) for r in results]
    strong_totals = [r["strong_score"].get("total", 0) for r in results]
    tgs_totals = [r["tgs_vs_strong"].get("total", 0) for r in results]
    gaps_tgs = sum(1 for r in results if r["gap_strong"])

    print(f"\n{'═'*60}\nAGGREGATE")
    print(f"  Single avg : {sum(single_totals)/len(single_totals):.1f}")
    print(f"  Strong avg : {sum(strong_totals)/len(strong_totals):.1f}")
    print(f"  TGS avg    : {sum(tgs_totals)/len(tgs_totals):.1f}")
    print(f"  Gap TGS    : {gaps_tgs}/{len(results)}")
    print("\nKEY QUESTION: Does TGS beat the strong baseline?")
    print("If yes — the procedures matter. If no — standard careful prompting is sufficient.")
    print("\nLIMITATIONS: LLM-as-judge biased toward longer/hedged answers. 3 questions not statistically significant.")

    with open("compare_results.json", "w") as f: json.dump(results, f, indent=2)
    print("\nSaved to compare_results.json")

if __name__ == "__main__": main()
