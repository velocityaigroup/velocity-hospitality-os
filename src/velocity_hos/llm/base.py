"""Backend-agnostic interfaces for embeddings and answering."""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class Embeddings(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text."""
        ...


@runtime_checkable
class LLM(Protocol):
    def answer(self, question: str, contexts: list[str]) -> str:
        """Answer ``question`` grounded strictly in ``contexts`` (retrieved SOPs)."""
        ...


SYSTEM_PROMPT = (
    "You are the SOP Coach for a hotel. Answer the staff member's question using "
    "ONLY the provided standard operating procedures (SOPs). Be concise and "
    "role-specific. If the SOPs do not contain the answer, say so plainly and "
    "suggest who to ask. Never invent policy."
)


def build_prompt(question: str, contexts: list[str]) -> str:
    joined = "\n\n".join(f"--- SOP excerpt {i+1} ---\n{c}" for i, c in enumerate(contexts))
    return (
        f"{joined}\n\n"
        f"Staff question: {question}\n\n"
        "Answer using only the SOP excerpts above."
    )
