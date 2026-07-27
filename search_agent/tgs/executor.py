"""Executor — encounter with resistance."""
from __future__ import annotations
import os, subprocess, sys, tempfile, textwrap
from dataclasses import dataclass
from typing import Optional

@dataclass
class ExecutionResult:
    success: bool; output: str; error: Optional[str]; returncode: int
    def as_text(self) -> str:
        parts = []
        if self.output: parts.append(f"OUTPUT:\n{self.output}")
        if self.error: parts.append(f"ERROR:\n{self.error}")
        parts.append(f"EXIT CODE: {self.returncode}")
        return "\n".join(parts)

def run_python(code: str, timeout: int = 15) -> ExecutionResult:
    code = textwrap.dedent(code).strip()
    tmp_path: Optional[str] = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(code); tmp_path = f.name
        result = subprocess.run([sys.executable, tmp_path], capture_output=True, text=True, timeout=timeout)
        return ExecutionResult(success=result.returncode == 0, output=result.stdout.strip(), error=result.stderr.strip() or None, returncode=result.returncode)
    except subprocess.TimeoutExpired:
        return ExecutionResult(success=False, output="", error=f"Timeout: execution exceeded {timeout}s", returncode=-1)
    except Exception as e:
        return ExecutionResult(success=False, output="", error=str(e), returncode=-1)
    finally:
        if tmp_path:
            try: os.unlink(tmp_path)
            except OSError: pass
