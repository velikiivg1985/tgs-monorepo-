#!/usr/bin/env python3
import os, sys
from tgs import TGSAgent

def main() -> None:
    args = sys.argv[1:]
    solve_mode = "--solve" in args
    args = [a for a in args if a != "--solve"]
    text = " ".join(args).strip() or ("write a function that sorts a graph topologically" if solve_mode else "What is the relationship between consciousness and information?")

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        print("Error: OPENAI_API_KEY is not set.\n  export OPENAI_API_KEY=sk-..."); sys.exit(1)

    try:
        agent = TGSAgent(api_key=api_key, model=os.environ.get("TGS_MODEL", "gpt-4o-mini"), base_url=os.environ.get("TGS_BASE_URL", "https://api.openai.com/v1"))
        agent.solve(text) if solve_mode else agent.ask(text)
    except KeyboardInterrupt:
        print("\nInterrupted."); sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}"); sys.exit(1)

if __name__ == "__main__": main()
