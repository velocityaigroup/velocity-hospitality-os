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


class LocalLLM:
    def answer(self, question: str, contexts: list[str]) -> str:
        if not contexts:
            return ("I couldn't find an SOP covering that. Please check with your "
                    "department head or the duty manager.")
        top = contexts[0].strip().replace("\n", " ")
        snippet = (top[:400] + "…") if len(top) > 400 else top
        return f"Per the property SOP: {snippet}"

    def summarize(self, instruction: str, sections: dict[str, list[str]]) -> str:
        total = sum(len(v) for v in sections.values())
        if total == 0:
            return "Daily briefing: all clear — no risks, staffing, revenue, or compliance alerts."
        body = render_sections(sections)
        return f"Daily briefing ({total} item(s) need attention):\n\n{body}"
