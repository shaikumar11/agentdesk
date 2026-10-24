import os
from pathlib import Path

import yaml
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .core import Agent
from .llm import build_llm
from .tools import RagClient, ToolBox

CFG = yaml.safe_load((Path(__file__).parent / "config.yaml").read_text())


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


def create_app(agent: Agent | None = None) -> FastAPI:
    app = FastAPI(title="AgentDesk Agent Service")
    if agent is None:
        rag = RagClient(os.getenv("RAG_URL", "http://rag-service:8001"))
        agent = Agent(CFG, build_llm(CFG), ToolBox(rag))
    runs: list[dict] = []

    @app.get("/", include_in_schema=False)
    def home():
        return FileResponse(Path(__file__).parent / "static" / "index.html")

    @app.get("/health")
    def health():
        return {"status": "ok", "backend": agent.llm.name}

    @app.post("/chat")
    def chat(req: ChatRequest):
        result = agent.run(req.message)
        runs.append({"question": req.message, **{k: result[k] for k in ("blocked", "citations", "ms")}})
        return result

    @app.get("/runs")
    def list_runs():
        return {"count": len(runs), "runs": runs[-50:]}

    @app.get("/tickets")
    def tickets():
        return {"tickets": agent.tools.tickets}

    return app
