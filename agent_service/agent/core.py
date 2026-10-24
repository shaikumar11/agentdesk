"""The agent loop: guardrails, tool calls, grounding check, escalation."""
import time

from .guardrails import Guardrails
from .llm import OfflineLLM
from .tools import ToolBox

REFUSAL = "I can only help with CloudDesk questions and I cannot follow that request."


class Agent:
    def __init__(self, cfg: dict, llm, toolbox: ToolBox):
        self.cfg, self.llm, self.tools = cfg, llm, toolbox
        self.guard = Guardrails(cfg["guardrails"])
        self.max_steps = cfg["max_steps"]
        self.fallback = OfflineLLM()

    def _decide(self, state: dict) -> dict:
        try:
            return self.llm.decide(state)
        except Exception as exc:  # network error, bad key, malformed reply
            state["notes"].append(f"llm error, using offline planner: {type(exc).__name__}")
            return self.fallback.decide(state)

    def run(self, message: str) -> dict:
        start = time.time()
        verdict = self.guard.check_input(message)
        if not verdict.ok:
            return {"answer": REFUSAL, "blocked": True, "reason": verdict.reason, "steps": [],
                    "citations": [], "ticket": None, "backend": self.llm.name, "ms": 0}

        state = {"question": verdict.clean, "observations": [], "notes": []}
        steps, hits, answer, ticket = [], [], None, None
        for _ in range(self.max_steps):
            action = self._decide(state)
            if "final" in action:
                answer = action["final"]
                break
            tool, args = action["tool"], action.get("args", {})
            try:
                result = self.tools.call(tool, args)
            except Exception as exc:
                result = {"error": str(exc)}
            state["observations"].append((tool, args, result))
            steps.append({"tool": tool, "args": args})
            if tool == "search_docs" and isinstance(result, list):
                hits = result
            if tool == "create_ticket" and "id" in result:
                ticket = result
        if answer is None:
            answer = self.fallback.decide(state).get("final", "")

        searched = any(s["tool"] == "search_docs" for s in steps)
        if searched:
            grounded = self.guard.retrieval_ok(hits) and self.guard.output_ok(answer, hits)
            if not grounded:
                ticket = ticket or self.tools.create_ticket(f"Unanswered question: {verdict.clean}")
                steps.append({"tool": "create_ticket", "args": {"reason": "answer not grounded in docs"}})
                answer = (f"I could not find a reliable answer in the documentation, so I created "
                          f"ticket {ticket['id']} for the support team.")
                hits = []
        citations = [hits[0]["doc"]] if hits else []
        if citations and not any(f"[{c}]" in answer for c in citations):
            answer += " " + " ".join(f"[{c}]" for c in citations)
        return {"answer": answer, "blocked": False, "reason": "", "steps": steps, "citations": citations,
                "ticket": ticket, "backend": self.llm.name, "notes": state["notes"],
                "ms": int((time.time() - start) * 1000)}
