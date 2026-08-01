# RAG & the SOP Coach

The SOP Coach demonstrates the retrieve-then-answer pattern end to end:

1. **Ingest** — the property's SOP library (`Context.sops`) is chunked and embedded
   into a vector store (`velocity_hos/rag/store.py`).
2. **Retrieve** — the staff question is embedded and the top-k nearest SOP excerpts
   are pulled by cosine similarity.
3. **Answer** — the configured AI provider answers grounded *only* in those excerpts;
   the response carries the source SOP ids for auditability. Retrieval, grounding and
   citations are **model-independent** — they do not change with the provider.

## AI providers
Selected by `VHOS_LLM_BACKEND` (see `velocity_hos/llm/`):

| Backend | Embeddings | Answering | Use |
|---------|-----------|-----------|-----|
| `local` (default) | hashed bag-of-words | extractive | tests, CI, offline dev |
| `openweights` | offline or open embeddings | self-hosted open-weights foundation model (vLLM) | official production (H200) |
| `bedrock` | Titan (optional) | any foundation model via the **Converse API** | managed cloud provider |

Switching the answering model is a **configuration change** (`VHOS_LLM_BACKEND`, and for
Bedrock `BEDROCK_MODEL_ID`) — never a code change. The same interface powers every agent.
