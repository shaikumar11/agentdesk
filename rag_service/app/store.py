"""Vector store backed by ChromaDB."""
from pathlib import Path

from collections import Counter

import chromadb

from .embed import embed
from .text import chunk_markdown, tokenize


class VectorStore:
    def __init__(self, persist_dir: str | None = None, name: str = "clouddesk_docs"):
        self.client = chromadb.PersistentClient(path=persist_dir) if persist_dir else chromadb.EphemeralClient()
        self.name = name
        self.col = None
        self.label_df: Counter = Counter()
        self.reset()

    def reset(self):
        try:
            self.client.delete_collection(self.name)
        except Exception:
            pass
        self.col = self.client.create_collection(self.name, metadata={"hnsw:space": "cosine"})

    def ingest_dir(self, docs_dir: str) -> int:
        self.reset()
        chunks = []
        for path in sorted(Path(docs_dir).glob("*.md")):
            chunks += chunk_markdown(path.read_text(encoding="utf-8"), path.stem)
        if not chunks:
            return 0
        # How many distinct headings contain each term: common terms like "plan" get no rerank boost.
        self.label_df = Counter(t for hd in {c["heading"] for c in chunks} for t in set(tokenize(hd)))
        self.col.add(
            ids=[f"{c['doc']}-{i}" for i, c in enumerate(chunks)],
            documents=[c["text"] for c in chunks],
            embeddings=[embed(c["heading"] + " " + c["text"]) for c in chunks],
            metadatas=[{"doc": c["doc"], "heading": c["heading"]} for c in chunks],
        )
        return len(chunks)

    def search(self, query: str, k: int = 3) -> list[dict]:
        if self.col.count() == 0:
            return []
        res = self.col.query(query_embeddings=[embed(query)], n_results=min(max(k * 3, 8), self.col.count()))
        hits = []
        for i in range(len(res["ids"][0])):
            hits.append({
                "id": res["ids"][0][i],
                "doc": res["metadatas"][0][i]["doc"],
                "heading": res["metadatas"][0][i]["heading"],
                "text": res["documents"][0][i],
                "score": round(1.0 - res["distances"][0][i], 4),  # cosine similarity
            })
        # Hybrid rerank: dense cosine score plus a boost when query terms appear in the heading.
        q_tokens = set(tokenize(query))
        for h in hits:
            label = set(tokenize(h["heading"]))
            h["score"] = round(h["score"] + min(0.08 * sum(1 for t in q_tokens & label if self.label_df[t] <= 2), 0.2), 4)
        hits.sort(key=lambda h: h["score"], reverse=True)
        return hits[:k]
