import os

from contextlib import asynccontextmanager

from fastapi import FastAPI, Query

from .store import VectorStore

DOCS_DIR = os.getenv("DOCS_DIR", os.path.join(os.path.dirname(__file__), "..", "docs"))
PERSIST_DIR = os.getenv("CHROMA_DIR") or None

store = VectorStore(PERSIST_DIR)


@asynccontextmanager
async def lifespan(_app):
    store.ingest_dir(DOCS_DIR)
    yield


app = FastAPI(title="AgentDesk RAG Service", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "chunks": store.col.count()}


@app.post("/ingest")
def ingest():
    return {"chunks": store.ingest_dir(DOCS_DIR)}


@app.get("/search")
def search(q: str = Query(..., min_length=2), k: int = Query(3, ge=1, le=10)):
    return {"query": q, "hits": store.search(q, k)}
