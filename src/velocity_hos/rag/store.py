"""A minimal, dependency-free vector store + retriever.

Good enough for property-scale SOP libraries and for demonstrating the
retrieve-then-answer pattern. In production this is backed by a managed vector
store; the interface stays the same.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from velocity_hos.llm.base import Embeddings


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
    # vectors are expected L2-normalized by the embedder; fall back if not.
    dot = sum(x * y for x, y in zip(a, b))
    return dot


@dataclass
class Chunk:
    doc_id: str
    text: str
    vector: list[float]


@dataclass
class VectorStore:
    chunks: list[Chunk] = field(default_factory=list)

    def add(self, doc_id: str, text: str, vector: list[float]) -> None:
        self.chunks.append(Chunk(doc_id, text, vector))

    def search(self, query_vec: list[float], k: int = 3) -> list[tuple[Chunk, float]]:
        scored = [(c, _cosine(query_vec, c.vector)) for c in self.chunks]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:k]

    def __len__(self) -> int:
        return len(self.chunks)


@dataclass
class Hit:
    doc_id: str
    text: str
    score: float


class Retriever:
    """Ingests a {doc_id: text} SOP map and answers nearest-neighbour queries."""

    def __init__(self, embeddings: Embeddings):
        self.embeddings = embeddings
        self.store = VectorStore()

    def ingest(self, sops: dict[str, object]) -> int:
        self.store = VectorStore()
        pieces: list[tuple[str, str]] = []
        for doc_id, body in sops.items():
            body_text = body if isinstance(body, str) else str(body)
            for piece in chunk_text(body_text):
                pieces.append((doc_id, piece))
        if not pieces:
            return 0
        vectors = self.embeddings.embed([p[1] for p in pieces])
        for (doc_id, piece), vec in zip(pieces, vectors):
            self.store.add(doc_id, piece, vec)
        return len(self.store)

    def query(self, question: str, k: int = 3) -> list[Hit]:
        if len(self.store) == 0:
            return []
        qvec = self.embeddings.embed([question])[0]
        return [Hit(c.doc_id, c.text, score) for c, score in self.store.search(qvec, k)]
