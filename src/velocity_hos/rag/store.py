"""A minimal, dependency-free hybrid retriever + vector store.

Retrieval fuses two signals so it is robust on a real property-scale SOP library:
  * DENSE — embedding cosine similarity (semantic match), backend-pluggable.
  * LEXICAL — IDF-weighted content-token overlap (exact-term match: "mojito",
    "work permit", "pour cost"), which dense offline embeddings alone under-weight.

The two rankings are combined with Reciprocal Rank Fusion (RRF), a parameter-light,
well-behaved fusion that needs no score calibration between the two spaces. Results
are de-duplicated to one hit per SOP so citations stay clean. In production the dense
half is backed by a managed vector store and a real embedding model; the interface
and the fusion stay identical.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from velocity_hos.llm.base import Embeddings
from .grounding import content_tokens, content_token_counts

_RRF_K = 60       # dense rank damping (dense magnitude is not calibrated cross-space)
_W_LEXICAL = 1.0  # lexical (TF-IDF) carries specific SOP terminology + keyword hits
_W_DENSE = 0.5    # dense adds paraphrase/semantics; leads only when lexical ties


def chunk_text(text: str, max_chars: int = 600, overlap: int = 80) -> list[str]:
    """Split text into overlapping character windows on paragraph/space breaks."""
    text = text.strip()
    if len(text) <= max_chars:
        return [text] if text else []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        if end < len(text):
            brk = text.rfind("\n", start, end)
            if brk == -1:
                brk = text.rfind(" ", start, end)
            if brk > start:
                end = brk
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return [c for c in chunks if c]


def _cosine(a: list[float], b: list[float]) -> float:
    # vectors are expected L2-normalized by the embedder; dot == cosine.
    return sum(x * y for x, y in zip(a, b))


@dataclass
class Chunk:
    doc_id: str
    text: str
    vector: list[float]
    counts: dict[str, int] = field(default_factory=dict)  # stemmed term frequencies


@dataclass
class VectorStore:
    chunks: list[Chunk] = field(default_factory=list)

    def add(self, doc_id: str, text: str, vector: list[float],
            counts: dict[str, int] | None = None) -> None:
        self.chunks.append(Chunk(doc_id, text, vector, counts or {}))

    def __len__(self) -> int:
        return len(self.chunks)


@dataclass
class Hit:
    doc_id: str
    text: str
    score: float


class Retriever:
    """Ingests a {doc_id: text} SOP map and answers hybrid (dense+lexical) queries."""

    def __init__(self, embeddings: Embeddings):
        self.embeddings = embeddings
        self.store = VectorStore()
        self._idf: dict[str, float] = {}

    def ingest(self, sops: dict[str, object]) -> int:
        self.store = VectorStore()
        pieces: list[tuple[str, str]] = []
        for doc_id, body in sops.items():
            body_text = body if isinstance(body, str) else str(body)
            for piece in chunk_text(body_text):
                pieces.append((doc_id, piece))
        if not pieces:
            self._idf = {}
            return 0
        vectors = self.embeddings.embed([p[1] for p in pieces])
        count_maps = [content_token_counts(p[1]) for p in pieces]
        for (doc_id, piece), vec, counts in zip(pieces, vectors, count_maps):
            self.store.add(doc_id, piece, vec, counts)
        self._idf = self._compute_idf([set(c) for c in count_maps])
        return len(self.store)

    @staticmethod
    def _compute_idf(token_sets: list[set[str]]) -> dict[str, float]:
        n = len(token_sets)
        df: dict[str, int] = {}
        for ts in token_sets:
            for t in ts:
                df[t] = df.get(t, 0) + 1
        # smoothed IDF; rarer terms (a specific SOP's keywords) weigh more.
        return {t: math.log(1 + n / d) for t, d in df.items()}

    def _lexical_score(self, qtokens: set[str], chunk: Chunk) -> float:
        """TF-IDF overlap: shared query terms weighted by rarity AND how often they
        occur in the chunk (so a term in the SOP title + keywords + body outscores a
        single incidental mention elsewhere)."""
        return sum(self._idf.get(t, 0.0) * chunk.counts.get(t, 0)
                   for t in qtokens if t in chunk.counts)

    def query(self, question: str, k: int = 3) -> list[Hit]:
        chunks = self.store.chunks
        if not chunks:
            return []
        qvec = self.embeddings.embed([question])[0]
        qtokens = content_tokens(question)

        lex_scores = [self._lexical_score(qtokens, c) for c in chunks]
        max_lex = max(lex_scores) or 1.0
        dense_rank = {i: r for r, i in enumerate(
            sorted(range(len(chunks)), key=lambda i: _cosine(qvec, chunks[i].vector),
                   reverse=True))}

        # Magnitude-aware hybrid: normalized lexical (leads, carries terminology) +
        # a bounded dense component (breaks ties, ranks paraphrases). Dense magnitude
        # is uncalibrated, so it enters via its rank, scaled to [0,1].
        fused: dict[int, float] = {}
        for i in range(len(chunks)):
            lex_norm = lex_scores[i] / max_lex
            dense_component = _RRF_K / (_RRF_K + dense_rank[i])  # rank0 -> 1.0
            fused[i] = _W_LEXICAL * lex_norm + _W_DENSE * dense_component

        order = sorted(fused, key=lambda i: fused[i], reverse=True)

        # De-duplicate to the best chunk per SOP, preserving fused order.
        hits: list[Hit] = []
        seen: set[str] = set()
        for i in order:
            c = chunks[i]
            if c.doc_id in seen:
                continue
            seen.add(c.doc_id)
            hits.append(Hit(c.doc_id, c.text, fused[i]))
            if len(hits) >= k:
                break
        return hits
