"""Backend-agnostic interfaces for embeddings and language generation."""
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

    def summarize(self, instruction: str, sections: dict[str, list[str]]) -> str:
        """Synthesize prose from labelled lists of items per ``instruction``."""
        ...


# --- SOP Coach prompting -------------------------------------------------------
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


# --- Executive briefing prompting ---------------------------------------------
BRIEFING_SYSTEM_PROMPT = (
    "You are the Executive Intelligence agent for a hotel group. Write a crisp "
    "daily briefing for the General Manager from the structured alerts provided. "
    "Lead with what needs a decision. Group by area, keep it scannable, and never "
    "invent items that are not in the data. If everything is clear, say so."
)


def render_sections(sections: dict[str, list[str]]) -> str:
    parts: list[str] = []
    for label, items in sections.items():
        if not items:
            continue
        bullets = "\n".join(f"- {it}" for it in items)
        parts.append(f"{label.replace('_', ' ').title()}:\n{bullets}")
    return "\n\n".join(parts) if parts else "(no alerts in any category)"
