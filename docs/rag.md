# RAG & the SOP Coach

The SOP Coach demonstrates the retrieve-then-answer pattern end to end:

1. **Ingest** — the property's SOP library (`Context.sops`) is chunked and embedded
   into a vector store (`velocity_hos/rag/store.py`).
2. **Retrieve** — the staff question is embedded and the top-k nearest SOP excerpts
   are pulled by cosine similarity.
3. **Answer** — the LLM answers grounded *only* in those excerpts; the response
   carries the source SOP ids for auditability.

## Backends
Selected by `VHOS_LLM_BACKEND` (see `velocity_hos/llm/`):

| Backend | Embeddings | Answering | Use |
|---------|-----------|-----------|-----|
| `local` (default) | hashed bag-of-words | extractive | tests, CI, offline dev |
| `bedrock` | Titan Text Embeddings v2 | Claude (messages API) | production / live demo |

Switch to Bedrock with AWS credentials configured:
```bash
export VHOS_LLM_BACKEND=bedrock
export AWS_REGION=us-east-1
python examples/sop_coach_demo.py
```

The same interface powers every agent, so the other six can adopt RAG the same way.
