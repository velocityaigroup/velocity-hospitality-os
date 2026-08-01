"""Grounding guardrail: decide whether retrieved SOPs actually support a question.

The SOP Coach must refuse to answer when the property's SOP library contains
nothing relevant — answering anyway is how RAG systems hallucinate policy. This
module provides a cheap, backend-agnostic relevance signal based on content-token
overlap between the question and the retrieved excerpts. It works with the offline
embeddings (whose scores are not calibrated for a global threshold) and complements
(does not replace) semantic scores from a production embedder.
"""
from __future__ import annotations

import re

# Small stopword set — enough to strip function words so only content tokens
# (domain nouns/verbs) drive the relevance signal.
_STOP = frozenset(
    ["a", "an", "the", "of", "to", "in", "on", "at", "for", "how", "do", "i", "we", "my", "me", "you", "it", "this", "that", "with", "and", "or", "is", "are", "was", "were", "be", "been", "being", "does", "did", "will", "can", "could", "should", "would", "may", "might", "if", "within", "any", "all", "least", "than", "time", "about", "into", "out", "over", "under", "then", "there", "here", "what", "when", "where", "who", "whom", "which", "why", "whose", "get", "got", "give", "tag", "as", "by", "from"]
)
_TOKEN = re.compile(r"[a-z0-9&]+")


def content_tokens(text: str) -> set[str]:
    """Lowercase content tokens (stopwords and 1–2 char tokens removed)."""
    return {t for t in _TOKEN.findall(text.lower()) if t not in _STOP and len(t) > 2}


def overlap_score(question: str, contexts: list[str]) -> int:
    """Max number of shared content tokens between the question and any excerpt."""
    q = content_tokens(question)
    if not q or not contexts:
        return 0
    return max((len(q & content_tokens(c)) for c in contexts), default=0)


def is_grounded(question: str, contexts: list[str], min_overlap: int = 1) -> bool:
    """True when retrieved excerpts share at least ``min_overlap`` content tokens."""
    return overlap_score(question, contexts) >= min_overlap
