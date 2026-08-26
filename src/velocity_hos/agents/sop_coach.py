"""2 - SOP Coach Agent (RAG-backed).

Answers "how do we do this here?" by retrieving the most relevant excerpts from
the property's own SOP library and having the LLM answer grounded strictly in
those excerpts. Every answer carries its source SOP ids for auditability.

Backend is pluggable (see ``velocity_hos.llm``): defaults to an offline local
backend; set ``VHOS_LLM_BACKEND`` to any AI provider (self-hosted open weights, or a
foundation model on Amazon Bedrock via the Converse API).
Components are injectable for testing.

Grounding guardrail: if the retrieved excerpts don't actually support the
question, the agent refuses and points the staff member to a human instead of
answering from thin air. This is what makes the assistant safe to put in front of
staff — it will say "I don't have an SOP for that" rather than invent policy.
"""
from __future__ import annotations

import re

from velocity_hos.llm import LLM, Embeddings, get_embeddings, get_llm
from velocity_hos.rag import Retriever, overlap_score

from .base import Agent, Context, Recommendation, RiskLevel

_REFUSAL = (
    "I couldn't find an SOP covering that. Please check with your department head "
    "or the duty manager."
)


def _mentions(question_lower: str, phrase: str) -> bool:
    """Word-boundary match for a single word; substring match for a phrase."""
    if " " in phrase or "-" in phrase:
        return phrase in question_lower
    return re.search(rf"\b{re.escape(phrase)}\b", question_lower) is not None


def match_known_gap(question: str, gaps: list[dict]) -> dict | None:
    """Return the declared knowledge gap this question falls into, if any.

    A property can declare gaps: subjects it has NOT yet given us documented answers
    for (rates, check-in times, transfer prices...). When a question lands in a
    declared gap the agent says so explicitly and routes to the responsible human,
    instead of answering from an adjacent SOP that merely shares vocabulary.

    This is a governance feature, not a retrieval trick: silence about what we do not
    know is what makes the assistant safe to put in front of a guest. A gap fires only
    when the question carries BOTH the gap's subject and the kind of detail it asks
    for, so questions the property HAS published answers to are unaffected.
    """
    q = (question or "").lower()
    for gap in gaps or []:
        terms = gap.get("terms") or []
        topics = gap.get("topic") or []
        if not terms or not topics:
            continue
        if any(_mentions(q, t) for t in terms) and any(_mentions(q, t) for t in topics):
            return gap
    return None


class SOPCoachAgent(Agent):
    name = "sop_coach"

    def __init__(
        self,
        embeddings: Embeddings | None = None,
        llm: LLM | None = None,
        top_k: int = 3,
        min_overlap: int = 2,
    ):
        self._retriever = Retriever(embeddings or get_embeddings())
        self._llm = llm or get_llm()
        self.top_k = top_k
        # Minimum number of distinct content-token matches between the question and a
        # retrieved SOP for the agent to answer. Requiring >=2 topical terms (not one
        # incidental word like "weather" or "stock") is what makes the grounding
        # guardrail reliably refuse out-of-scope questions instead of hallucinating.
        self.min_overlap = min_overlap

    def evaluate(self, ctx: Context) -> list[Recommendation]:
        question = ctx.inputs.get("question")
        if not question:
            return []

        # Declared knowledge gap -> refuse by name, before retrieval can find an
        # adjacent SOP that merely shares vocabulary with the question.
        gap = match_known_gap(question, ctx.inputs.get("known_gaps") or [])
        if gap is not None:
            owner = gap.get("owner") or "the duty manager"
            return [Recommendation(
                agent=self.name,
                summary=(
                    f"I don't have a documented answer for that — {gap['gap'].lower()}. "
                    f"Please check with {owner}, who can confirm it."
                ),
                risk=RiskLevel.INFO,
                proposed_action={"type": "refusal", "question": question,
                                 "reason": "declared_knowledge_gap",
                                 "gap_id": gap.get("gid"), "gap": gap.get("gap")},
                rationale=("The property has not yet supplied documentation on this "
                           "subject; answering would mean inventing policy."),
                sources=[],
            )]

        self._retriever.ingest(ctx.sops or {})
        hits = self._retriever.query(question, k=self.top_k)

        # Use the FULL text of each retrieved SOP as the context — for both the
        # grounding decision AND the answer — so a fact in a different chunk of the
        # right SOP isn't lost (retrieval de-dups to one best chunk per SOP). SOPs are
        # small, so passing the whole matched SOP is cheap and improves answer quality.
        contexts = [str(ctx.sops.get(h.doc_id, h.text)) for h in hits]
        grounded = overlap_score(question, contexts) >= self.min_overlap
        if not grounded:
            return [Recommendation(
                agent=self.name,
                summary=_REFUSAL,
                risk=RiskLevel.INFO,
                proposed_action={"type": "refusal", "question": question,
                                 "reason": "no_supporting_sop"},
                rationale="No property SOP supports this question; routed to a human.",
                sources=[],
            )]

        answer = self._llm.answer(question, contexts)
        return [Recommendation(
            agent=self.name,
            summary=answer,
            risk=RiskLevel.INFO,  # guidance only; never acts on a system
            proposed_action={"type": "answer", "question": question, "answer": answer},
            rationale="Answer grounded in retrieved property SOPs (RAG).",
            sources=[h.doc_id for h in hits],
        )]
