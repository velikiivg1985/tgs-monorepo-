"""TGS Agent — self-correcting through three procedures with adaptive routing."""
from __future__ import annotations
import re
import time
from dataclasses import dataclass
from openai import OpenAI

from .executor import ExecutionResult, run_python
from .geometry import Geometry
from .monitor import Signal, ExecutionSignal, ask as monitor_ask, ask_execution as monitor_ask_execution
from .search import Page, search
from .router import classify_task, Mode

_SYNTHESIS_SYSTEM = """You are a careful synthesiser. Apply three procedures:
1. Use the geometry as a lens, not as a conclusion.
2. Do not resolve what the sources leave unresolved. Show the structure of the conflict.
3. End with one specific condition under which this answer is wrong.
Format: plain text, 3-5 paragraphs. Final line: "This answer would be wrong if: [condition]"""

_CODE_SYSTEM = """You are a careful programmer. Write Python code that solves the task.
The code must be completely self-contained and runnable as-is. Include a simple test at the end.
Output ONLY the Python code. No explanation, no markdown fences."""

@dataclass
class SearchStep:
    number: int
    query: str
    pages: list[Page]
    signal: Signal
    geometry_snapshot: list[str]

@dataclass
class ExecutionStep:
    number: int
    code: str
    result: ExecutionResult
    signal: ExecutionSignal
    geometry_snapshot: list[str]

class TGSAgent:
    MAX_SEARCH_STEPS = 6
    MAX_EXECUTE_STEPS = 6
    STABILITY_WINDOW = 2

    def __init__(self, api_key: str, model: str = "gpt-4o-mini", base_url: str = "https://api.openai.com/v1") -> None:
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.geometry = Geometry()
        
        self._pages: list[Page] = []
        self._search_steps: list[SearchStep] = []
        self._execution_steps: list[ExecutionStep] = []
        self._recent_retracts: list[str] = []

    def _direct_answer(self, question: str) -> str:
        self._header("DIRECT MODE", question)
        return self._llm("Answer concisely and directly. No meta-commentary.", question, temperature=0.1, max_tokens=300)

    def _light_answer(self, question: str) -> str:
        self._header("LIGHT MODE", question)
        system = "Answer the technical question clearly. At the very end, add exactly one line: 'Falsification: This answer would be wrong if [condition].'"
        return self._llm(system, question, temperature=0.2, max_tokens=500)

    def ask(self, question: str) -> str:
        self._reset()
        self._header("ASK", question)
        mode, reason = classify_task(self.client, self.model, question)
        print(f"\n  [ROUTER] Mode: {mode.upper()} | Reason: {reason}\n")

        if mode == "direct": return self._direct_answer(question)
        if mode == "light": return self._light_answer(question)

        # Full TGS Mode
        query, stable_count = question, 0
        try:
            for n in range(1, self.MAX_SEARCH_STEPS + 1):
                pages = search(query)
                self._pages.extend(pages)
                self._print_search(n, query, pages)
                
                geo_before = self.geometry.size()
                signal = monitor_ask(client=self.client, model=self.model, question=question, geometry=self.geometry.current(), pages=pages)
                self._print_signal(signal)
                self._apply_search_signal(signal)
                geo_after = self.geometry.size()

                self._search_steps.append(SearchStep(number=n, query=query, pages=pages, signal=signal, geometry_snapshot=self.geometry.current()))

                if signal.done:
                    print(f"\n  → Monitor says done at step {n}.")
                    break
                
                if geo_before == geo_after and not signal.retract:
                    stable_count += 1
                    if stable_count >= self.STABILITY_WINDOW:
                        print(f"\n  → Geometry stable for {self.STABILITY_WINDOW} steps. Stopping.")
                        break
                else:
                    stable_count = 0

                if not signal.next_query: break
                query = signal.next_query

            return self._synthesise(question)
        except KeyboardInterrupt:
            print("\n  [agent] interrupted.")
            return ""
        except Exception as e:
            print(f"\n  [agent] error in ask(): {e}")
            return f"Error: {e}"

    def solve(self, task: str) -> str:
        self._reset()
        self._header("SOLVE", task)
        mode, reason = classify_task(self.client, self.model, task)
        print(f"\n  [ROUTER] Mode: {mode.upper()} | Reason: {reason}\n")

        if mode == "direct": return self._direct_answer(task)
        
        # FIX: For light mode in solve, we still generate and run code, but skip deep search
        if mode == "light":
            print("  → Light mode: generating code without deep search research.")
            code = self._write_code(task)
            result = run_python(code)
            self._print_result(result)
            self._print_report()
            return code

        try:
            query, stable_count = task, 0
            for n in range(1, self.MAX_SEARCH_STEPS + 1):
                pages = search(query)
                self._pages.extend(pages)
                self._print_search(n, query, pages)
                
                geo_before = self.geometry.size()
                signal = monitor_ask(client=self.client, model=self.model, question=task, geometry=self.geometry.current(), pages=pages)
                self._print_signal(signal)
                self._apply_search_signal(signal)
                geo_after = self.geometry.size()

                self._search_steps.append(SearchStep(number=n, query=query, pages=pages, signal=signal, geometry_snapshot=self.geometry.current()))

                if signal.done: break
                if geo_before == geo_after and not signal.retract:
                    stable_count += 1
                    if stable_count >= self.STABILITY_WINDOW: break
                else: stable_count = 0
                
                if not signal.next_query: break
                query = signal.next_query

            code = self._write_code(task)
            for n in range(1, self.MAX_EXECUTE_STEPS + 1):
                self._print_execute_header(n, code)
                result = run_python(code)
                self._print_result(result)
                
                signal_e = monitor_ask_execution(client=self.client, model=self.model, task=task, geometry=self.geometry.current(), code=code, result=result)
                self._print_execution_signal(signal_e)
                self._apply_execution_signal(signal_e)

                self._execution_steps.append(ExecutionStep(number=n, code=code, result=result, signal=signal_e, geometry_snapshot=self.geometry.current()))

                if signal_e.done or signal_e.next_action == "done":
                    print(f"\n  → Done at execution step {n}.")
                    break

                if signal_e.next_action == "fix_code" and signal_e.corrected_code:
                    code = signal_e.corrected_code
                elif signal_e.next_action == "search_more" and signal_e.next_query:
                    extra = search(signal_e.next_query)
                    self._pages.extend(extra)
                    extra_signal = monitor_ask(client=self.client, model=self.model, question=task, geometry=self.geometry.current(), pages=extra)
                    self._apply_search_signal(extra_signal)
                    if extra_signal.geometry_changed: code = self._write_code(task)
                else:
                    break

            self._print_report()
            return code
        except KeyboardInterrupt:
            print("\n  [agent] interrupted.")
            return ""
        except Exception as e:
            print(f"\n  [agent] error in solve(): {e}")
            return f"Error: {e}"

    def _llm(self, system: str, user: str, temperature: float = 0.4, max_tokens: int = 1000) -> str:
        for attempt in range(1, 4):
            try:
                response = self.client.chat.completions.create(
                    model=self.model, temperature=temperature, max_tokens=max_tokens,
                    messages=[{"role": "system", "content": system}, {"role": "user", "content": user}]
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                if attempt < 3:
                    print(f"  [llm] attempt {attempt} failed: {e}")
                    time.sleep(2.0)
                else:
                    print(f"  [llm] all retries failed: {e}")
        return ""

    def _write_code(self, task: str) -> str:
        raw = self._llm(_CODE_SYSTEM, f"TASK: {task}\nGEOMETRY: {self.geometry.current()}", temperature=0.3, max_tokens=1200)
        return _extract_code(raw) if raw else "# Code generation failed."

    def _synthesise(self, question: str) -> str:
        pages_text = "\n\n".join(p.text() for p in self._pages)
        answer = self._llm(_SYNTHESIS_SYSTEM, f"QUESTION: {question}\nGEOMETRY (lens): {self.geometry.current()}\nRETRACTED: {self.geometry.retracted()}\nPAGES:\n{pages_text}", temperature=0.5, max_tokens=800)
        self._print_answer(answer or "Synthesis failed.")
        self._print_report()
        return answer or "Synthesis failed."

    def _apply_search_signal(self, signal: Signal) -> None:
        if signal.retract and not self._is_pingpong(signal.retract):
            if self.geometry.retract(signal.retract):
                self._recent_retracts.append(signal.retract)
                print(f"\n  ◇ Retracted: '{signal.retract}'\n    {self.geometry}")
        if signal.geometry_changed and signal.invariant and self.geometry.add(signal.invariant):
            print(f"\n  ◆ Added: '{signal.invariant}'")
            if signal.falsification: print(f"    Wrong if: {signal.falsification}")
            print(f"    {self.geometry}")

    def _apply_execution_signal(self, signal: ExecutionSignal) -> None:
        if signal.retract and not self._is_pingpong(signal.retract):
            if self.geometry.retract(signal.retract):
                self._recent_retracts.append(signal.retract)
                print(f"\n  ◇ Retracted (exec): '{signal.retract}'\n    {self.geometry}")
        if signal.geometry_changed and signal.invariant and self.geometry.add(signal.invariant):
            print(f"\n  ◆ Added (exec): '{signal.invariant}'")
            if signal.falsification: print(f"    Wrong if: {signal.falsification}")
            print(f"    {self.geometry}")

    def _is_pingpong(self, invariant: str) -> bool:
        from .geometry import _similar
        return sum(1 for r in self._recent_retracts if _similar(r, invariant)) >= 2

    def _reset(self) -> None:
        self.geometry = Geometry()
        self._pages = []
        self._search_steps = []
        self._execution_steps = []
        self._recent_retracts = []

    def _header(self, mode: str, text: str) -> None:
        print(f"\n{'═'*62}\n  TGS AGENT — {mode}\n{'═'*62}\n  {text}\n  Model : {self.model}")

    def _print_search(self, n: int, query: str, pages: list) -> None:
        print(f"\n{'─'*62}\n  SEARCH STEP {n}\n  Query : {query}\n  Found : {len(pages)} page(s)")
        for p in pages: print(f"    · {p.title[:56]}")

    def _print_signal(self, s: Signal) -> None:
        print(f"\n  Monitor:\n    blind spot    : {s.blind_spot or '—'}\n    invariant     : {s.invariant or '—'}\n    retract       : {s.retract or '—'}\n    falsification : {s.falsification or '—'}\n    done          : {s.done}\n    next query    : {s.next_query or '—'}")

    def _print_execute_header(self, n: int, code: str) -> None:
        lines = code.splitlines()
        print(f"\n{'─'*62}\n  EXECUTE STEP {n}  ({len(lines)} lines)")
        for line in lines[:6]: print(f"    {line}")
        if len(lines) > 6: print(f"    ... ({len(lines) - 6} more lines)")

    def _print_result(self, r: ExecutionResult) -> None:
        print(f"\n  Execution : {'✓ success' if r.success else '✗ failed'}")
        if r.output: print(f"  Output    : {r.output[:200]}")
        if r.error: print(f"  Error     : {r.error[:200]}")

    def _print_execution_signal(self, s: ExecutionSignal) -> None:
        print(f"\n  Monitor (exec):\n    blind spot    : {s.blind_spot or '—'}\n    invariant     : {s.invariant or '—'}\n    retract       : {s.retract or '—'}\n    falsification : {s.falsification or '—'}\n    next action   : {s.next_action}\n    done          : {s.done}")

    def _print_answer(self, answer: str) -> None:
        print(f"\n{'═'*62}\n  ANSWER\n{'═'*62}\n")
        for line in answer.splitlines(): print(f"  {line}")

    def _print_report(self) -> None:
        print(f"\n{'─'*62}\n  REPORT\n    Search steps    : {len(self._search_steps)}\n    Execution steps : {len(self._execution_steps)}\n    Final geometry  : {self.geometry}")
        if self.geometry.retracted(): print(f"    Retracted       : {self.geometry.retracted()}")
        if self._execution_steps:
            failures = sum(1 for s in self._execution_steps if not s.result.success)
            print(f"    Failures used   : {failures}")
        if self.geometry.grew(): print(f"\n  Self-correction occurred.")

def _extract_code(raw: str) -> str:
    # FIX: Restored correct triple backticks regex
    blocks = re.findall(r"```(?:python)?\s*\n(.*?)```", raw, re.DOTALL)
    return max(blocks, key=len).strip() if blocks else raw.strip()
  
