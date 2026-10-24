import os

import pytest
from fastapi.testclient import TestClient

from app.embed import embed
from app.text import chunk_markdown, tokenize

DOCS = os.path.join(os.path.dirname(__file__), "..", "docs")


@pytest.fixture(scope="module")
def client():
    os.environ["DOCS_DIR"] = DOCS
    from app.main import app
    with TestClient(app) as c:
        yield c


def test_tokenize_drops_stopwords_and_stems():
    assert tokenize("The limits are exceeded") == ["limit", "exceed"]


def test_embedding_is_unit_length_and_deterministic():
    a, b = embed("rate limit"), embed("rate limit")
    assert a == b
    assert abs(sum(x * x for x in a) - 1.0) < 1e-6


def test_chunking_keeps_headings():
    chunks = chunk_markdown("# T\n\n## A\none\n\n## B\ntwo", "d")
    assert [c["heading"] for c in chunks] == ["A", "B"]


def test_health_reports_chunks(client):
    r = client.get("/health").json()
    assert r["status"] == "ok" and r["chunks"] >= 8


@pytest.mark.parametrize("q,doc", [
    ("how do I verify webhook signatures", "webhooks"),
    ("what is the rate limit on the growth plan", "rate-limits"),
    ("how long are tickets kept before deletion", "data-retention"),
    ("what does http 409 mean", "errors"),
])
def test_search_finds_right_doc(client, q, doc):
    hits = client.get("/search", params={"q": q, "k": 3}).json()["hits"]
    assert hits[0]["doc"] == doc


def test_search_validates_input(client):
    assert client.get("/search", params={"q": "x"}).status_code == 422
