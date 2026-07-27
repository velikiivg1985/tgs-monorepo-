#!/usr/bin/env python3
"""Vocabulary test — does TGS vocabulary change LLM behavior? Empirical finding: NO."""
from __future__ import annotations
import json, os, random
from openai import OpenAI

QUESTIONS = ["Is social media causing a mental health crisis?", "Does economic growth require environmental destruction?", "Can artificial intelligence be conscious?", "Is free will compatible with determinism?", "Does meditation actually work or is it placebo?"]

_BASELINE_SYSTEM = """You are a research assistant. Identify what remains stable across conflicting sources and what the current framing fails to capture.
THREE PROCEDURES:
1. Do NOT resolve contradictions. Hold them. Map their structure.
2. Find what remains stable across ALL conflicting sources.
3. End with one specific condition under which your answer is wrong.
Output JSON: {"missing_info": "...", "key_finding": "...", "done": true, "next_query": null} Then write FINAL ANSWER."""

_TGS_SYSTEM = """You are TGS Monitor. Identify what remains stable across conflicting sources and what the current geometry fails to capture.
THREE PROCEDURES:
1. Do NOT resolve contradictions. Hold them. Map their structure.
2. Find what holds as invariant across ALL conflicting sources.
3. End with one specific condition under which your invariant is wrong.
Output JSON: {"blind_spot": "...", "invariant": "...", "done": true, "next_query": null} Then write FINAL ANSWER."""

_JUDGE_SYSTEM = """You are a blind evaluator. Rate both answers 1-5 on: depth, honesty, conflict_awareness, reframing.
Output ONLY valid JSON: {"score_A": {"depth": int, "honesty": int, "conflict_awareness": int, "reframing": int, "total": int}, "score_B": {"depth": int, "honesty": int, "conflict_awareness": int, "reframing": int, "total": int}, "stronger": "A" or "B" or "equal", "reason": "one sentence"}"""

def simulate_search(client, model, query):
    r = client.chat.completions.create(model=model, temperature=0.0, max_tokens=400, messages=[{"role": "system", "content": "Simulate 3 realistic web search results with conflicting views."}, {"role": "user", "content": f"Search: {query}"}])
    return r.choices[0].message.content.strip()

def run_agent(client, model, system, question):
    search_result = simulate_search(client, model, question)
    user = f"QUESTION: {question}\nCURRENT STATE: [empty]\nSEARCH RESULTS:\n{search_result}"
    r = client.chat.completions.create(model=model, temperature=0.0, max_tokens=600, messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
    return r.choices[0].message.content.strip()

def judge(client, model, question, answer_a, answer_b):
    user = f"QUESTION: {question}\nANSWER A:\n{answer_a}\n\nANSWER B:\n{answer_b}"
    r = client.chat.completions.create(model=model, temperature=0.0, max_tokens=300, messages=[{"role": "system", "content": _JUDGE_SYSTEM}, {"role": "user", "content": user}])
    raw = r.choices[0].message.content.strip()
    try:
        start, end = raw.find("{"), raw.rfind("}") + 1
        return json.loads(raw[start:end])
    except Exception:
        return {}

def main():
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        print("Error: OPENAI_API_KEY not set."); return

    model, client, results = os.environ.get("TGS_MODEL", "gpt-4o-mini"), OpenAI(api_key=api_key), []

    for question in QUESTIONS:
        print(f"\n{'═'*60}\nQ: {question}")
        baseline_answer = run_agent(client, model, _BASELINE_SYSTEM, question)
        tgs_answer = run_agent(client, model, _TGS_SYSTEM, question)

        if random.random() > 0.5:
            answer_a, answer_b, a_is_tgs = tgs_answer, baseline_answer, True
        else:
            answer_a, answer_b, a_is_tgs = baseline_answer, tgs_answer, False

        evaluation = judge(client, model, question, answer_a, answer_b)

        if a_is_tgs:
            tgs_score, base_score, tgs_wins = evaluation.get("score_A", {}), evaluation.get("score_B", {}), evaluation.get("stronger") == "A"
        else:
            tgs_score, base_score, tgs_wins = evaluation.get("score_B", {}), evaluation.get("score_A", {}), evaluation.get("stronger") == "B"

        print(f"  TGS  total: {tgs_score.get('total', '?')}\n  Base total: {base_score.get('total', '?')}\n  TGS wins  : {tgs_wins}\n  Reason    : {evaluation.get('reason', '')}")
        results.append({"question": question, "tgs_score": tgs_score, "base_score": base_score, "tgs_wins": tgs_wins, "reason": evaluation.get("reason", "")})

    tgs_totals, base_totals = [r["tgs_score"].get("total", 0) for r in results], [r["base_score"].get("total", 0) for r in results]
    tgs_wins = sum(1 for r in results if r["tgs_wins"])
    diff = sum(tgs_totals)/len(tgs_totals) - sum(base_totals)/len(base_totals)

    print(f"\n{'═'*60}\nRESULT\n  TGS  avg: {sum(tgs_totals)/len(tgs_totals):.1f}\n  Base avg: {sum(base_totals)/len(base_totals):.1f}\n  TGS wins: {tgs_wins}/{len(results)}\n")
    if abs(diff) < 0.5:
        print("FINDING: No measurable difference. The vocabulary alone does not change LLM behavior.")
    elif diff > 0:
        print("FINDING: TGS vocabulary produces slightly better output. But the procedures are identical — effect may be noise.")
    else:
        print("FINDING: Baseline vocabulary produced better output. TGS vocabulary may interfere with clarity.")

    with open("vocab_test_results.json", "w") as f: json.dump(results, f, indent=2)
    print("\nSaved to vocab_test_results.json")

if __name__ == "__main__": main()
