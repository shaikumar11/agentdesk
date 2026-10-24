"""Tools the agent can call. Each returns plain JSON serialisable data."""
import ast
import operator

import httpx

_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.Pow: operator.pow, ast.USub: operator.neg, ast.Mod: operator.mod}


def safe_eval(expr: str) -> float:
    """Evaluate arithmetic only, never arbitrary code."""
    def ev(n):
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return n.value
        if isinstance(n, ast.BinOp) and type(n.op) in _OPS:
            if isinstance(n.op, ast.Pow) and abs(ev(n.right)) > 10:
                raise ValueError("exponent too large")
            return _OPS[type(n.op)](ev(n.left), ev(n.right))
        if isinstance(n, ast.UnaryOp) and type(n.op) in _OPS:
            return _OPS[type(n.op)](ev(n.operand))
        raise ValueError("unsupported expression")
    return ev(ast.parse(expr, mode="eval").body)


class RagClient:
    def __init__(self, base_url: str = "http://rag-service:8001", http: httpx.Client | None = None):
        self.http = http or httpx.Client(base_url=base_url, timeout=60.0)  # free hosts need time to wake up

    def search(self, query: str, k: int = 3) -> list[dict]:
        r = self.http.get("/search", params={"q": query, "k": k})
        r.raise_for_status()
        return r.json()["hits"]


class ToolBox:
    def __init__(self, rag: RagClient):
        self.rag = rag
        self.tickets: list[dict] = []

    def search_docs(self, query: str) -> list[dict]:
        return self.rag.search(query)

    def create_ticket(self, summary: str, priority: str = "P3") -> dict:
        if priority not in ("P1", "P2", "P3"):
            priority = "P3"
        ticket = {"id": f"TCK-{1001 + len(self.tickets)}", "summary": summary[:200], "priority": priority}
        self.tickets.append(ticket)
        return ticket

    def calculate(self, expression: str) -> float:
        return round(safe_eval(expression), 4)

    def call(self, name: str, args: dict):
        if name not in ("search_docs", "create_ticket", "calculate"):
            raise ValueError(f"unknown tool {name}")
        return getattr(self, name)(**args)


TOOL_SCHEMAS = [
    {"type": "function", "function": {"name": "search_docs", "description": "Search the CloudDesk documentation.",
     "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "create_ticket", "description": "Create a support ticket.",
     "parameters": {"type": "object", "properties": {"summary": {"type": "string"},
                    "priority": {"type": "string", "enum": ["P1", "P2", "P3"]}}, "required": ["summary"]}}},
    {"type": "function", "function": {"name": "calculate", "description": "Evaluate an arithmetic expression.",
     "parameters": {"type": "object", "properties": {"expression": {"type": "string"}}, "required": ["expression"]}}},
]
