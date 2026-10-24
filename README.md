# AgentDesk

A small production style GenAI support agent for a fictional SaaS product, built as two Docker based microservices.

```
client -> agent-service (FastAPI, :8000) -> rag-service (FastAPI + ChromaDB, :8001)
```

**rag-service** chunks markdown docs, builds embeddings, stores them in ChromaDB and serves `/search`. Retrieval is hybrid: cosine similarity from the vector DB plus a heading term boost.

**agent-service** runs the agent loop. Instructions, tools and guardrails are defined in `agent/config.yaml`.

| Concern | How it is handled |
|---|---|
| Tool calling | `search_docs`, `create_ticket`, `calculate` (safe AST evaluator, no `eval`) |
| LLM backend | Groq (OpenAI compatible tool calling) when `GROQ_API_KEY` is set, otherwise a deterministic offline planner. If the LLM call fails the agent falls back to the offline planner |
| Input guardrails | Prompt injection patterns, length limit, email and phone redaction before any tool call |
| Output guardrails | Retrieval score threshold and a grounding check against retrieved text. Ungrounded answers are replaced and a support ticket is created |
| Citations | Every grounded answer cites its source doc, for example `[rate-limits]` |

## Run

```bash
docker compose up --build
curl -s localhost:8000/chat -H 'content-type: application/json' \
  -d '{"message":"What is the rate limit on the Growth plan?"}'
```

Optional: `export GROQ_API_KEY=...` before `docker compose up` to use a hosted LLM.

## Web UI and hosting

Open `http://localhost:8000/` for a chat page (answers, source tags, tool steps, tickets). To host it publicly for free:

1. Push this repo to GitHub.
2. On render.com choose New, then Blueprint, and select the repo. `render.yaml` creates both services.
3. Optional: add `GROQ_API_KEY` on the `agentdesk` service to switch from the offline planner to a hosted LLM.
4. If Render gives `agentdesk-rag` a different URL, set `RAG_URL` on `agentdesk` to it.

Free services sleep after 15 minutes idle, so the first request can take about a minute.

## Endpoints

`POST /chat`, `GET /runs`, `GET /tickets`, `GET /health` (agent). `GET /search?q=`, `POST /ingest`, `GET /health` (rag).

## Test and evaluate

```bash
pip install -r rag_service/requirements.txt -r agent_service/requirements.txt
(cd rag_service && python -m pytest -q)     # 9 tests
(cd agent_service && python -m pytest -q)   # 11 tests
python eval/run_eval.py                     # 22 case end to end eval
```

The eval covers answerable questions, out of scope questions that must escalate, injection attempts that must be blocked, calculator use and ticket creation. It is a small set and retrieval was tuned against it, so treat the score as a regression check, not a benchmark.

## Limits and next steps

- Embeddings are a hashing vectorizer so the project runs offline. Replace `embed()` with a hosted or sentence transformer model for better recall.
- Ticket store and run history are in memory. Move them to PostgreSQL for persistence.
