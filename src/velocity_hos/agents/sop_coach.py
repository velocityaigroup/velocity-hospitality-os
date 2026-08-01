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

from velocity_hos.llm import LLM, Embeddings, get_embeddings, get_llm
from velocity_hos.rag import Retriever, overlap_score

from .base import Agent, Context, Recommendation, RiskLevel

_REFUSAL = (
    "I couldn't find an SOP covering that. Please check with your department head "
    "or the duty manager."
)


class SOPCoachAgent(Agent):
    name = "sop_coach"

    def __init__(
        self,
        embeddings: Embeddings | None = None,
        llm: LLM | None = None,
        top_k: int = 3,
        min_overlap: int = 1,
    ):
        self._retriever = Retriever(embeddings or get_embeddings())
        self._llm = llm or get_llm()
        self.top_k = top_k
        # Minimum content-token overlap between question and retrieved SOPs for
        # the agent to answer. Below this it refuses (grounding guardrail).
        self.min_overlap = min_overlap

    def evaluate(self, ctx: Context) -> list[Recommendation]:
        question = ctx.inputs.get("question")
        if not question:
            return []

        self._retriever.ingest(ctx.sops or {})
        hits = self._retriever.query(question, k=self.top_k)
        contexts = [h.text for h in hits]

        # Guardrail: refuse rather than answer when nothing relevant was retrieved.
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
