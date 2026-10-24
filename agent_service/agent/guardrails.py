"""Input and output guardrails for the agent."""
import re
from dataclasses import dataclass

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE = re.compile(r"(?<!\d)(?:\+?\d[\d\s-]{8,14}\d)(?!\d)")
_WORD = re.compile(r"[a-z0-9]+")
_STOP = {"a", "an", "the", "is", "are", "was", "to", "of", "and", "or", "in", "on", "for", "with",
         "at", "by", "it", "this", "that", "as", "from", "can", "be", "if", "you", "your", "so", "not"}


def content_words(text: str) -> set[str]:
    return {w[:5] for w in _WORD.findall(text.lower()) if w not in _STOP and len(w) > 2}


def redact_pii(text: str) -> str:
    return PHONE.sub("[phone]", EMAIL.sub("[email]", text))


@dataclass
class InputVerdict:
    ok: bool
    reason: str = ""
    clean: str = ""


class Guardrails:
    def __init__(self, cfg: dict):
        self.max_chars = cfg["max_input_chars"]
        self.min_score = cfg["min_retrieval_score"]
        self.min_grounding = cfg["min_grounding"]
        self.patterns = [re.compile(p, re.I) for p in cfg["injection_patterns"]]

    def check_input(self, message: str) -> InputVerdict:
        if not message.strip():
            return InputVerdict(False, "empty message")
        if len(message) > self.max_chars:
            return InputVerdict(False, "message too long")
        for p in self.patterns:
            if p.search(message):
                return InputVerdict(False, "prompt injection attempt")
        return InputVerdict(True, clean=redact_pii(message))

    def retrieval_ok(self, hits: list[dict]) -> bool:
        return bool(hits) and hits[0]["score"] >= self.min_score

    def grounding(self, answer: str, hits: list[dict]) -> float:
        """Share of the answer's content words that appear in the retrieved text."""
        words = content_words(re.sub(r"\[[\w-]+\]", "", answer))
        if not words:
            return 0.0
        source = set().union(*(content_words(h["text"]) for h in hits)) if hits else set()
        return len(words & source) / len(words)

    def output_ok(self, answer: str, hits: list[dict]) -> bool:
        return self.grounding(answer, hits) >= self.min_grounding
