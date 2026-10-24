"""Deterministic hashing embedding: unigrams + bigrams hashed into a fixed size vector.

It needs no model download, so the service runs offline and tests are reproducible.
Swap embed() for a hosted or local embedding model to improve recall.
"""
import math
import zlib

from .text import tokenize

DIM = 1024


def embed(text: str) -> list[float]:
    toks = tokenize(text)
    grams = toks + [f"{a}_{b}" for a, b in zip(toks, toks[1:])]
    vec = [0.0] * DIM
    for g in grams:
        h = zlib.crc32(g.encode())
        sign = 1.0 if (h >> 16) & 1 else -1.0
        vec[h % DIM] += sign
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]
