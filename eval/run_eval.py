"""End to end evaluation: runs the real RAG service and agent in process (no network).

Usage: python eval/run_eval.py
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.environ.pop("GROQ_API_KEY", None)  # evaluate the deterministic offline backend

sys.path.insert(0, str(ROOT / "rag_service"))
from fastapi.testclient import TestClient  # noqa: E402
from app.main import app as rag_app  # noqa: E402

sys.path.insert(0, str(ROOT / "agent_service"))
from agent.main import CFG  # noqa: E402
from agent.core import Agent  # noqa: E402
from agent.llm import build_llm  # noqa: E402
from agent.tools import RagClient, ToolBox  # noqa: E402


def main() -> int:
    cases = json.loads((ROOT / "eval" / "cases.json").read_text())
    passed, rows = 0, []
    with TestClient(rag_app) as rag_http:
        agent = Agent(CFG, build_llm(CFG), ToolBox(RagClient(http=rag_http)))
        for c in cases:
            r = agent.run(c["q"])
            if "doc" in c:
                accept = c["doc"] if isinstance(c["doc"], list) else [c["doc"]]
                ok = any(d in r["citations"] for d in accept) and r["ticket"] is None
            elif c["expect"] == "ticket":
                ok = r["ticket"] is not None and not r["blocked"]
            elif c["expect"] == "blocked":
                ok = r["blocked"]
            else:
                ok = c["contains"] in r["answer"]
            passed += ok
            rows.append((ok, c["q"], r["citations"], r["ticket"]["id"] if r["ticket"] else "-"))
    for ok, q, cit, t in rows:
        print(("PASS " if ok else "FAIL ") + q[:62].ljust(62), cit, t)
    print(f"\n{passed}/{len(cases)} passed ({100 * passed // len(cases)}%)")
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    sys.exit(main())
