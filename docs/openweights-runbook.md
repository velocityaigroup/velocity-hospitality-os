# Runbook — self-hosted open-weights model (OFFICIAL deployment)

Velocity's official inference path is an **open-weights model we serve ourselves** — no
managed-API dependency, no vendor lock-in. The LLM is a swappable provider behind one
interface; retrieval, guardrails, citations, evaluation and workflow logic never change.

## Model selection (as of 2026)
- **Production (H200): `Qwen3.6-27B` (Apache-2.0, ~262K context).** Best practical
  quality/latency on a single H200 (141 GB HBM3e) with full context and headroom for
  concurrency; permissive license fits an open-source competition. Confirm the exact HF
  repo id when you pull it. Alternatives: Nemotron-3-Super or a DeepSeek V4 Flash (MoE) if
  you want a larger model and it fits.
- **Local proof (today): any small instruct model via Ollama** (e.g. a 3–9B Qwen/Gemma/
  Ministral). Validates the *entire* inference path — UI → agent → RAG → grounded, cited
  answer — on a laptop, before the H200 is provisioned.

## A. Local proof — do this today (Ollama)
```bash
# install Ollama (ollama.com), then:
ollama pull qwen3            # or any small instruct model you have
export VHOS_LLM_BACKEND=openweights
export VHOS_EMBED_BACKEND=local
export VHOS_OPENWEIGHTS_URL=http://localhost:11434/v1
export VHOS_OPENWEIGHTS_MODEL=qwen3
python scripts/openweights_smoketest.py     # green = a real open model answered
python ui/server.py                         # open http://localhost:8080 — the working UI
python demo/run_demo.py                     # the end-to-end hero loop
```

## B. Production — H200 with vLLM
```bash
pip install vllm
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen3.6-27B-Instruct \
  --max-model-len 32768 --port 8000
# point Velocity at the GPU host:
export VHOS_LLM_BACKEND=openweights
export VHOS_EMBED_BACKEND=local          # or serve an embedding model too (see below)
export VHOS_OPENWEIGHTS_URL=http://<gpu-host>:8000/v1
export VHOS_OPENWEIGHTS_MODEL=Qwen/Qwen3.6-27B-Instruct
python scripts/openweights_smoketest.py
python demo/run_demo.py
python eval/run_eval.py     # capture accuracy on the production model
```
Screenshot the vLLM server log + the demo/eval output — that proves it's running on the
provided compute, not a managed API.

## Embeddings
The fast path keeps offline embeddings (`VHOS_EMBED_BACKEND=local`) so nothing blocks on
an embedding model. To use open-weights embeddings, serve one (e.g. `BAAI/bge-*`) on an
OpenAI-compatible endpoint and set `VHOS_EMBED_BACKEND=openweights` + `VHOS_OPENWEIGHTS_EMBED_MODEL`.

## Why this is the right call
Some managed foundation models are **entitlement-gated** on our AWS account (they return
403 "not available for this account"). Rather than wait on an enterprise unlock, Velocity
runs on open weights on the provided compute — which is *more* aligned with an open-source
agentic-AI competition. The Bedrock Converse provider (running an available foundation
model such as Amazon Nova) and other provider adapters remain in the repo as optional
alternatives; none are required.

## Honesty
Distinguish clearly: the **local proof model** validates the path today; the **H200
Qwen3.6-27B** is the deployment target. Don't claim H200 numbers until it's actually served
there — the same eval prints the real figure when you run it against the GPU.
