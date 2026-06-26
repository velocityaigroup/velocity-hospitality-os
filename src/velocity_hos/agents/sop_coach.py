"""2 - SOP Coach Agent (RAG-backed).

Answers "how do we do this here?" by retrieving the most relevant excerpts from
the property's own SOP library and having the LLM answer grounded strictly in
those excerpts. Every answer carries its source SOP ids for auditability.

Backend is pluggable (see ``velocity_hos.llm``): defaults to an offline local
backend; set ``VHOS_LLM_BACKEND=bedrock`` to use Amazon Bedrock (Titan + Claude).
Components are injectable for testing.
"""
from __future__ import annotations

from velocity_hos.llm import LLM, Embeddings, get_embeddings, get_llm
from velocity_hos.rag import Retriever

from .base import Agent, Context, Recommendation, RiskLevel


class SOPCoachAgent(Agent):
    name = "sop_coach"

    def __init__(
        self,
        embeddings: Embeddings | None = None,
        llm: LLM | None = None,
        top_k: int = 3,
    ):
        self._retriever = Retriever(embeddings or get_embeddings())
        self._llm = llm or get_llm()
        self.top_k = top_k

    def evaluate(self, ctx: Context) -> list[Recommendation]:
        question = ctx.inputs.get("question")
        if not question:
            return []

        self._retriever.ingest(ctx.sops or {})
        hits = self._retriever.query(question, k=self.top_k)
        contexts = [h.text for h in hits]
        answer = self._llm.answer(question, contexts)

        return [Recommendation(
            agent=self.name,
            summary=answer,
            risk=RiskLevel.INFO,  # guidance only; never acts on a system
            proposed_action={"type": "answer", "question": question, "answer": answer},
            rationale="Answer grounded in retrieved property SOPs (RAG).",
            sources=[h.doc_id for h in hits],
        )]
