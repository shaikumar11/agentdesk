"""Tokenization and chunking for the RAG service."""
import re

STOP = {
    "a", "an", "the", "is", "are", "was", "were", "be", "to", "of", "and", "or", "in", "on",
    "for", "with", "at", "by", "it", "this", "that", "as", "from", "can", "do", "does", "how",
    "what", "which", "my", "your", "i", "we", "you", "me", "if", "will", "all", "any",
}
_WORD = re.compile(r"[a-z0-9]+")

# Small query/document synonym map so different wordings land on the same token.
SYNONYMS = {"retained": "retention", "retain": "retention", "kept": "retention", "keep": "retention"}


def stem(word: str) -> str:
    for suffix in ("ing", "ion", "ed", "es", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[: -len(suffix)]
    return word


def tokenize(text: str) -> list[str]:
    """Lowercase, split on non alphanumerics, drop stop words, light stemming."""
    return [stem(SYNONYMS.get(w, w)) for w in _WORD.findall(text.lower()) if w not in STOP]


def chunk_markdown(text: str, doc: str, max_chars: int = 500) -> list[dict]:
    """Split a markdown file by heading, then pack paragraphs up to max_chars."""
    chunks, heading, buf = [], doc, []

    def flush():
        body = " ".join(buf).strip()
        if body:
            chunks.append({"doc": doc, "heading": heading, "text": body})
        buf.clear()

    for line in text.splitlines():
        if line.startswith("#"):
            flush()
            heading = line.lstrip("# ").strip() or doc
        elif line.strip():
            if sum(len(x) for x in buf) + len(line) > max_chars:
                flush()
            buf.append(line.strip())
    flush()
    return chunks
