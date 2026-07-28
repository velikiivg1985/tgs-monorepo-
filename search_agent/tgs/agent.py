"""
TGS Agent v3.4 — probe-based self-routing.

Two modes:
    ask(question)   epistemic: corrects errors of framing
    solve(task)     pragmatic: corrects errors of execution

Routing logic (v3.4):
    OLD: external router classified query type, then chose mode.
    NEW: triviality guard + probe encounter decides mode.

    Stage 1: triviality guard (router.py)
        Catches obvious arithmetic, factual lookups, micro-code.
        Returns direct answer without search or monitor.

    Stage 2: probe encounter
        One real search (max_results=2).
        One monitor call.
        System inspects the signal and decides:
            direct  = done=True, no blind_spot, no change
            light   = some signal, no major conflict
            full    = blind_spot / geometry_changed / retract / next_query

    Stage 3: mode execution
        direct → _answer_factual()
        light  → _synthesise() immediately
        full   → full search loop → _synthesise()

Why this is TGS-consistent:
    The old router decided from the label of the question.
    The new probe decides from the encounter with the environment.
    The system observes what actually happens when it looks,
    then decides how much looking is needed.

Empirically validated:
    The three procedures in monitor.py produce measurably different
    output from standard prompting — not the vocabulary.
    See experiments/vocab_test.py.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from openai import OpenAI

from .executor  import ExecutionResult, run_python
from .geometry  import Geometry
from .router    import is_obviously_trivial, triviality_reason
from .monitor   import (
    Signal,
    ExecutionSignal,
    ask           as monitor_ask,
    ask_execution as monitor_ask_execution,
)
from .search import Page, search


# ── LLM prompts ────────────────────────────────────────────────────────────────

_DIRECT_SYSTEM = """
You are a precise assistant. Answer the question directly and concisely.
Maximum accuracy. No meta-commentary. No TGS vocabulary.
If the answer is a number or a date, give only that.
"""

_SYNTHESIS_SYSTEM = """
You are a careful synthesiser. You apply three procedures:

1. Use the geometry as a lens, not as a conclusion.
   The geometry tells you what structure to look through.
   The pages give you the content to look at.

2. Do not resolve what the sources leave unresolved.
   Show the structure of the conflict. Do not pick a side.

3. End with one specific condition under which this answer is wrong.
   Not a vague hedge — a concrete falsification condition.

You receive:
- question
- geometry: invariants discovered through search
- retracted: invariants that turned out to be wrong
- pages: all pages found

Format: plain text, 3-5 paragraphs.
Final line: "This answer would be wrong if: [condition]"
"""

_CODE_SYSTEM = """
You are a careful programmer.

You receive:
- task: what needs to be done
- geometry: structural invariants discovered through research

Write Python code that solves the task.
The code must be completely self-contained and runnable as-is.
Include a simple test at the end that verifies the result.
Output ONLY the Python code. No explanation. No markdown fences.
"""


# ── Internal records ───────────────────────────────────────────────────────────

@dataclass
class SearchStep:
    number           : int
    query            : str
    pages            : list[Page]
    signal           : Signal
    geometry_snapshot: list[str]


@dataclass
class ExecutionStep:
    number           : int
    code             : str
    result           : ExecutionResult
    signal           : ExecutionSignal
    geometry_snapshot: list[str]


@dataclass
class ProbeResult:
    pages  : list[Page]
    signal : Signal
    mode   : str   # "direct" | "light" | "full"
    reason : str


# ── Agent ──────────────────────────────────────────────────────────────────────

class TGSAgent:
    """
    TGS self-correcting agent with probe-based self-routing.

    Usage:
        agent = TGSAgent(api_key="sk-...")
        answer = agent.ask("what is the hard problem of consciousness?")
        code   = agent.solve("write a topological sort that handles cycles")
    """

    MAX_SEARCH_STEPS  = 5
    MAX_EXECUTE_STEPS = 5
    STABILITY_WINDOW  = 2
    LLM_RETRIES       = 3
    LLM_PAUSE         = 2.0

    def __init__(
        self,
        api_key : str,
        model   : str = "gpt-4o-mini",
        base_url: str = "https://api.openai.com/v1",
    ) -> None:
        self.client   = OpenAI(api_key=api_key, base_url=base_url)
        self.model    = model
        self.geometry = Geometry()

        self._pages           : list[Page]           = []
        self._search_steps    : list[SearchStep]     = []
        self._execution_steps : list[ExecutionStep]  = []
        self._recent_retracts : list[str]            = []
        self._probe_result    : ProbeResult | None   = None

    # ── Public: epistemic mode ─────────────────────────────────────────────────

    def ask(self, question: str) -> str:
        """
        Answer a question through probe-based self-routing.

        Routing stages:
            1. Triviality guard  → direct answer if obviously trivial
            2. Probe encounter   → system decides mode from signal
            3. Mode execution    → direct / light / full TGS loop
        """
        self._reset()

        # Stage 1: triviality guard
        trivial_reason = triviality_reason(question)
        if trivial_reason:
            self._header(f"ASK [direct-guard: {trivial_reason}]", question)
            return self._answer_direct(question)

        # Stage 2: probe
        probe = self._run_probe(question)
        self._probe_result = probe

        self._header(f"ASK [probe→{probe.mode}]", question)
        self._print_probe(probe)

        # Stage 3: mode execution
        if probe.mode == "direct":
            return self._answer_direct(question)

        # Apply probe signal to geometry
        self._pages.extend(probe.pages)
        self._apply_search_signal(probe.signal)

        if probe.mode == "light":
            return self._synthesise(question)

        # Full loop — continue from where probe left off
        query = probe.signal.next_query or question
        stable_count = 0

        try:
            for n in range(1, self.MAX_SEARCH_STEPS + 1):
                pages = search(query, fetch_full=True)
                self._pages.extend(pages)
                self._print_search(n, query, pages)

                geo_before = self.geometry.size()

                signal = monitor_ask(
                    client   = self.client,
                    model    = self.model,
                    question = question,
                    geometry = self.geometry.current(),
                    pages    = pages,
                )
                self._print_signal(signal)
                self._apply_search_signal(signal)

                geo_after = self.geometry.size()

                self._search_steps.append(SearchStep(
                    number=n,
                    query=query,
                    pages=pages,
                    signal=signal,
                    geometry_snapshot=self.geometry.current(),
                ))

                if signal.done:
                    print(f"\n  → Monitor: done at step {n}.")
                    break

                # Adaptive stop: geometry stable
                if geo_before == geo_after and not signal.retract:
                    stable_count += 1
                    if stable_count >= self.STABILITY_WINDOW:
                        print(
                            f"\n  → Geometry stable for "
                            f"{self.STABILITY_WINDOW} steps. Stopping."
                        )
                        break
                else:
                    stable_count = 0

                if not signal.next_query:
                    break

                query = signal.next_query

            return self._synthesise(question)

        except KeyboardInterrupt:
            print("\n  [agent] interrupted.")
            return ""
        except Exception as e:
            print(f"\n  [agent] error in ask(): {e}")
            return f"Error: {e}"

    # ── Public: pragmatic mode ─────────────────────────────────────────────────

    def solve(self, task: str) -> str:
        """
        Solve a task that requires writing and running code.

        Routing:
            trivial guard     → execute-first without research
            probe → direct    → execute-first without research
            probe → light/full → research then execute
        """
        self._reset()

        # Stage 1: triviality guard
        trivial_reason = triviality_reason(task)
        if trivial_reason:
            self._header(f"SOLVE [direct-guard: {trivial_reason}]", task)
            return self._execute_loop(task)

        # Stage 2: probe
        probe = self._run_probe(task)
        self._probe_result = probe

        self._header(f"SOLVE [probe→{probe.mode}]", task)
        self._print_probe(probe)

        # Stage 3: decide research vs execute-first
        if probe.mode in ("direct", "light"):
            # Skip research — go straight to execution
            print("\n  → Probe: no deep conflict. Execute-first mode.")
            self._pages.extend(probe.pages)
            self._apply_search_signal(probe.signal)
            return self._execute_loop(task)

        # Full mode: research first
        self._pages.extend(probe.pages)
        self._apply_search_signal(probe.signal)

        query = probe.signal.next_query or task

        try:
            for n in range(1, self.MAX_SEARCH_STEPS + 1):
                pages = search(query, fetch_full=False)
                self._pages.extend(pages)
                self._print_search(n, query, pages)

                signal = monitor_ask(
                    client   = self.client,
                    model    = self.model,
                    question = task,
                    geometry = self.geometry.current(),
                    pages    = pages,
                )
                self._print_signal(signal)
                self._apply_search_signal(signal)

                self._search_steps.append(SearchStep(
                    number=n,
                    query=query,
                    pages=pages,
                    signal=signal,
                    geometry_snapshot=self.geometry.current(),
                ))

                if signal.done or not signal.next_query:
                    break

                query = signal.next_query

        except KeyboardInterrupt:
            print("\n  [agent] interrupted during research.")
            return ""

        return self._execute_loop(task)

    # ── Probe ──────────────────────────────────────────────────────────────────

    def _run_probe(self, question: str) -> ProbeResult:
        """
        One real search + one monitor call.
        The signal determines routing: direct / light / full.

        This is the TGS-consistent replacement for external routing.
        The system decides its own depth from the first encounter.
        """
        print(f"\n  [probe] searching...")
        pages = search(question, max_results=2, fetch_full=False)

        signal = monitor_ask(
            client   = self.client,
            model    = self.model,
            question = question,
            geometry = self.geometry.current(),
            pages    = pages,
        )

        mode, reason = self._decide_mode(signal)

        return ProbeResult(
            pages=pages,
            signal=signal,
            mode=mode,
            reason=reason,
        )

    def _decide_mode(self, signal: Signal) -> tuple[str, str]:
        """
        Decide routing mode from probe signal.

        direct:
            Monitor says done. No blind spot. No geometry change.
            The question has a clear answer that the probe already found.

        light:
            Some signal, but no major unresolved conflict.
            Synthesise from probe results only.

        full:
            Real blind spot, or geometry changed, or retraction needed,
            or next_query points to something deeper.
            Run the full TGS search loop.
        """
        has_blind    = bool(signal.blind_spot)
        has_new      = bool(signal.geometry_changed and signal.invariant)
        has_retract  = bool(signal.retract)
        has_next     = bool(signal.next_query)
        is_done      = bool(signal.done)

        if is_done and not has_blind and not has_new and not has_retract:
            return "direct", "monitor: done with no new signal"

        if has_blind or has_new or has_retract or has_next:
            reasons = []
            if has_blind:
                reasons.append(f"blind_spot={signal.blind_spot[:40]!r}")
            if has_new:
                reasons.append(f"new_invariant={signal.invariant[:40]!r}")
            if has_retract:
                reasons.append(f"retract={signal.retract[:30]!r}")
            if has_next:
                reasons.append(f"next_query='{signal.next_query[:30]}'")
            return "full", "; ".join(reasons)

        return "light", "some signal but no major conflict"

    # ── Internal: LLM calls ────────────────────────────────────────────────────

    def _llm(
        self,
        system      : str,
        user        : str,
        temperature : float = 0.4,
        max_tokens  : int   = 1000,
    ) -> str:
        for attempt in range(1, self.LLM_RETRIES + 1):
            try:
                response = self.client.chat.completions.create(
                    model       = self.model,
                    temperature = temperature,
                    max_tokens  = max_tokens,
                    messages    = [
                        {"role": "system", "content": system},
                        {"role": "user",   "content": user},
                    ],
                )
                return response.choices[0].message.content.strip()

            except Exception as e:
                if attempt < self.LLM_RETRIES:
                    print(f"  [llm] attempt {attempt} failed: {e}")
                    time.sleep(self.LLM_PAUSE)
                else:
                    print(f"  [llm] all retries failed: {e}")

        return ""

    def _answer_direct(self, question: str) -> str:
        """Lightweight single-shot response for trivial queries."""
        answer = self._llm(
            _DIRECT_SYSTEM, question,
            temperature=0.1, max_tokens=200,
        )
        self._print_answer(answer)
        return answer

    def _synthesise(self, question: str) -> str:
        pages_text = "\n\n".join(p.text() for p in self._pages)
        user = "\n\n".join([
            f"QUESTION: {question}",
            f"GEOMETRY (lens): {self.geometry.current()}",
            f"RETRACTED (were wrong): {self.geometry.retracted()}",
            f"PAGES:\n{pages_text}",
        ])
        answer = self._llm(
            _SYNTHESIS_SYSTEM, user,
            temperature=0.5, max_tokens=800,
        )
        if not answer:
            answer = "Synthesis failed."
        self._print_answer(answer)
        self._print_report()
        return answer

    def _write_code(self, task: str) -> str:
        user = "\n\n".join([
            f"TASK: {task}",
            f"GEOMETRY: {self.geometry.current()}",
        ])
        raw = self._llm(
            _CODE_SYSTEM, user,
            temperature=0.2, max_tokens=1200,
        )
        if not raw:
            return "# Code generation failed."
        return _extract_code(raw)

    def _execute_loop(self, task: str) -> str:
        """
        Write code → run → monitor → correct → repeat.
        """
        code = self._write_code(task)

        for n in range(1, self.MAX_EXECUTE_STEPS + 1):
            self._print_execute_header(n, code)
            result = run_python(code)
            self._print_result(result)

            signal_e = monitor_ask_execution(
                client   = self.client,
                model    = self.model,
                task     = task,
                geometry = self.geometry.current(),
                code     = code,
                result   = result,
            )
            self._print_execution_signal(signal_e)
            self._apply_execution_signal(signal_e)

            self._execution_steps.append(ExecutionStep(
                number=n,
                code=code,
                result=result,
                signal=signal_e,
                geometry_snapshot=self.geometry.current(),
            ))

            if signal_e.done or signal_e.next_action == "done":
                print(f"\n  → Done at execution step {n}.")
                break

            if signal_e.next_action == "fix_code":
                if signal_e.corrected_code:
                    code = signal_e.corrected_code
                else:
                    break

            elif signal_e.next_action == "search_more":
                if signal_e.next_query:
                    extra = search(signal_e.next_query, fetch_full=False)
                    self._pages.extend(extra)
                    extra_signal = monitor_ask(
                        client   = self.client,
                        model    = self.model,
                        question = task,
                        geometry = self.geometry.current(),
                        pages    = extra,
                    )
                    self._apply_search_signal(extra_signal)
                    if extra_signal.geometry_changed:
                        code = self._write_code(task)
                else:
                    break
            else:
                break

        self._print_report()
        return code

    # ── Internal: geometry updates ─────────────────────────────────────────────

    def _apply_search_signal(self, signal: Signal) -> None:
        if signal.retract:
            if self._is_pingpong(signal.retract):
                print(f"\n  ⚠ Ping-pong: '{signal.retract}' — skipping.")
            else:
                removed = self.geometry.retract(signal.retract)
                if removed:
                    self._recent_retracts.append(signal.retract)
                    print(f"\n  ◇ Retracted: '{signal.retract}'")
                    print(f"    {self.geometry}")

        if signal.geometry_changed and signal.invariant:
            added = self.geometry.add(signal.invariant)
            if added:
                print(f"\n  ◆ Added: '{signal.invariant}'")
                if signal.falsification:
                    print(f"    Wrong if: {signal.falsification}")
                print(f"    {self.geometry}")

    def _apply_execution_signal(self, signal: ExecutionSignal) -> None:
        if signal.retract:
            if self._is_pingpong(signal.retract):
                print(f"\n  ⚠ Ping-pong: '{signal.retract}' — skipping.")
            else:
                removed = self.geometry.retract(signal.retract)
                if removed:
                    self._recent_retracts.append(signal.retract)
                    print(f"\n  ◇ Retracted (exec): '{signal.retract}'")
                    print(f"    {self.geometry}")

        if signal.geometry_changed and signal.invariant:
            added = self.geometry.add(signal.invariant)
            if added:
                print(f"\n  ◆ Added (exec): '{signal.invariant}'")
                if signal.falsification:
                    print(f"    Wrong if: {signal.falsification}")
                print(f"    {self.geometry}")

    def _is_pingpong(self, invariant: str) -> bool:
        from .geometry import _similar
        return sum(
            1 for r in self._recent_retracts
            if _similar(r, invariant)
        ) >= 2

    # ── Internal: reset ────────────────────────────────────────────────────────

    def _reset(self) -> None:
        self.geometry          = Geometry()
        self._pages            = []
        self._search_steps     = []
        self._execution_steps  = []
        self._recent_retracts  = []
        self._probe_result     = None

    # ── Internal: display ──────────────────────────────────────────────────────

    def _header(self, mode: str, text: str) -> None:
        print(f"\n{'═'*62}")
        print(f"  TGS AGENT — {mode}")
        print(f"{'═'*62}")
        print(f"  {text}")
        print(f"  Model : {self.model}")

    def _print_probe(self, probe: ProbeResult) -> None:
        print(f"\n{'─'*62}")
        print(f"  PROBE")
        print(f"  Found   : {len(probe.pages)} page(s)")
        print(f"  Mode    : {probe.mode}")
        print(f"  Reason  : {probe.reason}")
        print(f"\n  Probe signal:")
        print(f"    blind_spot    : {probe.signal.blind_spot    or '—'}")
        print(f"    invariant     : {probe.signal.invariant     or '—'}")
        print(f"    retract       : {probe.signal.retract       or '—'}")
        print(f"    falsification : {probe.signal.falsification or '—'}")
        print(f"    done          : {probe.signal.done}")
        print(f"    next_query    : {probe.signal.next_query    or '—'}")

    def _print_search(self, n: int, query: str, pages: list) -> None:
        print(f"\n{'─'*62}")
        print(f"  SEARCH STEP {n}")
        print(f"  Query : {query}")
        print(f"  Found : {len(pages)} page(s)")
        for p in pages:
            print(f"    · {p.title[:56]}")

    def _print_signal(self, s: Signal) -> None:
        print(f"\n  Monitor (three procedures):")
        print(f"    blind_spot    : {s.blind_spot    or '—'}")
        print(f"    invariant     : {s.invariant     or '—'}")
        print(f"    retract       : {s.retract       or '—'}")
        print(f"    falsification : {s.falsification or '—'}")
        print(f"    done          : {s.done}")
        print(f"    next_query    : {s.next_query    or '—'}")

    def _print_execute_header(self, n: int, code: str) -> None:
        lines = code.splitlines()
        print(f"\n{'─'*62}")
        print(f"  EXECUTE STEP {n}  ({len(lines)} lines)")
        for line in lines[:6]:
            print(f"    {line}")
        if len(lines) > 6:
            print(f"    ... ({len(lines) - 6} more lines)")

    def _print_result(self, r: ExecutionResult) -> None:
        status = "✓ success" if r.success else "✗ failed"
        print(f"\n  Execution : {status}")
        if r.output:
            print(f"  Output    : {r.output[:200]}")
        if r.error:
            print(f"  Error     : {r.error[:200]}")

    def _print_execution_signal(self, s: ExecutionSignal) -> None:
        print(f"\n  Monitor (four procedures):")
        print(f"    blind_spot    : {s.blind_spot    or '—'}")
        print(f"    invariant     : {s.invariant     or '—'}")
        print(f"    retract       : {s.retract       or '—'}")
        print(f"    falsification : {s.falsification or '—'}")
        print(f"    next_action   : {s.next_action}")
        print(f"    done          : {s.done}")

    def _print_answer(self, answer: str) -> None:
        print(f"\n{'═'*62}")
        print(f"  ANSWER")
        print(f"{'═'*62}\n")
        for line in answer.splitlines():
            print(f"  {line}")

    def _print_report(self) -> None:
        print(f"\n{'─'*62}")
        print(f"  REPORT")
        print(f"    Probe mode      : {self._probe_result.mode if self._probe_result else 'guard'}")
        print(f"    Search steps    : {len(self._search_steps)}")
        print(f"    Execution steps : {len(self._execution_steps)}")
        print(f"    Final geometry  : {self.geometry}")
        if self.geometry.retracted():
            print(f"    Retracted       : {self.geometry.retracted()}")
        if self._execution_steps:
            failures = sum(
                1 for s in self._execution_steps
                if not s.result.success
            )
            print(f"    Failures used   : {failures}")
        if self.geometry.grew():
            print(f"\n  Self-correction occurred.")


# ── Helpers ────────────────────────────────────────────────────────────────────

def _extract_code(raw: str) -> str:
    """Extract Python code. Takes the largest block if multiple exist."""
    blocks = re.findall(r"```(?:python)?\s*\n(.*?)```", raw, re.DOTALL)
    if blocks:
        return max(blocks, key=len).strip()
    return raw.strip()
