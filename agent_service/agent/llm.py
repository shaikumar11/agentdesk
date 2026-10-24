"""LLM backends. Both expose decide(state) -> {"tool", "args"} or {"final"}.

GroqLLM uses the OpenAI compatible tool calling API. OfflineLLM is a rule based planner so the
whole system runs and is testable with no API key.
"""
import json
import os
import re

import httpx

from .tools import TOOL_SCHEMAS

TICKET = re.compile(r"\b(create|open|raise|file|log)\b.{0,15}\bticket\b|\bescalate\b", re.I)
MATH = re.compile(r"(\d[\d.,]*\s*[-+*/x]\s*\d[\d.,]*(?:\s*[-+*/x]\s*\d[\d.,]*)*)")


def _first_sentences(text: str, n: int = 2) -> str:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return " ".join(parts[:n])


class OfflineLLM:
    name = "offline"

    def decide(self, state: dict) -> dict:
        q, obs = state["question"], state["observations"]
        if not obs:
            if TICKET.search(q):
                return {"tool": "create_ticket", "args": {"summary": q, "priority": "P2" if "urgent" in q.lower() else "P3"}}
            m = MATH.search(q)
            if m:
                return {"tool": "calculate", "args": {"expression": m.group(1).replace("x", "*").replace(",", "")}}
            return {"tool": "search_docs", "args": {"query": q}}
        tool, _args, result = obs[-1]
        if tool == "calculate":
            return {"final": f"The result is {result}."}
        if tool == "create_ticket":
            return {"final": f"I created ticket {result['id']} with priority {result['priority']}."}
        if tool == "search_docs" and result:
            top = result[0]
            return {"final": f"{_first_sentences(top['text'])} [{top['doc']}]"}
        return {"final": "I could not find that in the documentation."}


class GroqLLM:
    name = "groq"
    URL = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(self, api_key: str, model: str, instructions: str, client: httpx.Client | None = None):
        self.model, self.instructions = model, instructions
        self.http = client or httpx.Client(timeout=30.0)
        self.headers = {"Authorization": f"Bearer {api_key}", "User-Agent": "agentdesk/1.0",
                        "Content-Type": "application/json"}

    def _messages(self, state: dict) -> list[dict]:
        msgs = [{"role": "system", "content": self.instructions},
                {"role": "user", "content": state["question"]}]
        for i, (tool, args, result) in enumerate(state["observations"]):
            cid = f"call_{i}"
            msgs.append({"role": "assistant", "content": None, "tool_calls": [
                {"id": cid, "type": "function", "function": {"name": tool, "arguments": json.dumps(args)}}]})
            msgs.append({"role": "tool", "tool_call_id": cid, "content": json.dumps(result)[:3000]})
        return msgs

    def decide(self, state: dict) -> dict:
        body = {"model": self.model, "messages": self._messages(state), "tools": TOOL_SCHEMAS,
                "tool_choice": "auto", "temperature": 0.1}
        r = self.http.post(self.URL, headers=self.headers, json=body)
        r.raise_for_status()
        msg = r.json()["choices"][0]["message"]
        calls = msg.get("tool_calls")
        if calls:
            fn = calls[0]["function"]
            return {"tool": fn["name"], "args": json.loads(fn["arguments"] or "{}")}
        return {"final": (msg.get("content") or "").strip()}


def build_llm(cfg: dict):
    key = os.getenv("GROQ_API_KEY")
    if key:
        return GroqLLM(key, os.getenv("GROQ_MODEL", cfg["model"]), cfg["instructions"])
    return OfflineLLM()
