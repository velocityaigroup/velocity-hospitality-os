"""Deterministic, dependency-free backend for tests, demos, and offline dev.

Embeddings use hashed bag-of-words; the LLM does extractive grounding and
template-based summarization. No network, no credentials.
"""
from __future__ import annotations

import hashlib
import math
import re

from .base import render_sections

_DIM = 256
_TOKEN = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


class LocalEmbeddings:
    dim = _DIM

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._one(t) for t in texts]

    @staticmethod
    def _one(text: str) -> list[float]:
        vec = [0.0] * _DIM
        for tok in _tokens(text):
            idx = int(hashlib.md5(tok.encode()).hexdigest(), 16) % _DIM
            vec[idx] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


_SENT = re.compile(r"(?<=[.!?])\s+|\n+")


class LocalLLM:
    def answer(self, question: str, contexts: list[str]) -> str:
        if not contexts:
            return ("I couldn't find an SOP covering that. Please check with your "
                    "department head or the duty manager.")
        # Extractive answer: return the sentence(s) from the retrieved SOP most
        # relevant to the question (by content-token overlap), not just the opening
        # lines — so the actual answer fact isn't truncated away. (The production
        # backends generate a natural-language answer from the same context.)
        qtokens = set(_tokens(question)) - {"how", "what", "much", "many", "does", "the", "for"}
        sentences: list[str] = []
        for ctx in contexts[:2]:
            # Skip the retrieval header ("SOP-ID — Title (Department)") and the
            # keyword line: neither is an answer, and both match question terms
            # strongly enough to crowd out the sentence that actually answers.
            lines = [ln for ln in str(ctx).splitlines()
                     if ln.strip() and not ln.startswith("Keywords:")][1:]
            for ln in lines:
                sentences += [s.strip() for s in _SENT.split(ln) if len(s.strip()) > 3]
        if not sentences:
            return f"Per the property SOP: {contexts[0].strip()[:300]}"
        scored = sorted(
            enumerate(sentences),
            key=lambda it: (len(qtokens & set(_tokens(it[1]))), -it[0]),
            reverse=True,
        )
        best = [s for _, s in sorted(scored[:2], key=lambda it: it[0])]
        return "Per the property SOP: " + " ".join(best).replace("\n", " ")

    def summarize(self, instruction: str, sections: dict[str, list[str]]) -> str:
        total = sum(len(v) for v in sections.values())
        if total == 0:
            return "Daily briefing: all clear — no risks, staffing, revenue, or compliance alerts."
        body = render_sections(sections)
        return f"Daily briefing ({total} item(s) need attention):\n\n{body}"
