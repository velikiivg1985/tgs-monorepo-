"""Tests for tgs/executor.py — real subprocess execution."""
from __future__ import annotations
from tgs.executor import run_python, ExecutionResult

class TestRunPython:
    def test_success(self):
        r = run_python("print('hello')"); assert r.success is True; assert r.output == "hello"; assert r.error is None; assert r.returncode == 0
    def test_failure(self):
        r = run_python("raise ValueError('test')"); assert r.success is False; assert r.error is not None; assert "ValueError" in r.error
    def test_syntax_error(self):
        r = run_python("def broken(:"); assert r.success is False; assert r.error is not None
    def test_timeout(self):
        r = run_python("while True: pass", timeout=1); assert r.success is False; assert "Timeout" in r.error
    def test_zero_division(self):
        r = run_python("x = 1/0"); assert r.success is False; assert "ZeroDivisionError" in r.error
    def test_output_captured(self):
        r = run_python("for i in range(3): print(i)"); assert r.success is True; assert "0" in r.output; assert "2" in r.output
    def test_multiline_code(self):
        r = run_python("def add(a, b):\n    return a + b\nprint(add(2, 3))"); assert r.success is True; assert r.output == "5"
    def test_import_stdlib(self):
        r = run_python("import json; print(json.dumps({'a': 1}))"); assert r.success is True; assert '"a"' in r.output

class TestExecutionResult:
    def test_as_text_success(self):
        r = ExecutionResult(success=True, output="hello", error=None, returncode=0); text = r.as_text()
        assert "OUTPUT" in text; assert "hello" in text; assert "EXIT CODE: 0" in text
    def test_as_text_failure(self):
        r = ExecutionResult(success=False, output="", error="ZeroDivisionError", returncode=1); text = r.as_text()
        assert "ERROR" in text; assert "ZeroDivisionError" in text
    def test_as_text_no_output(self):
        r = ExecutionResult(success=True, output="", error=None, returncode=0); text = r.as_text()
        assert "EXIT CODE: 0" in text
