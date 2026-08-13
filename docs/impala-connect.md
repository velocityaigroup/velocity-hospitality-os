# Running Velocity on the provided Buildathon compute (Impala gateway)

The Future Caribbean Buildathon provisions an **open-weights model — Qwen 3.6 27B —
on the Impala gateway**, an OpenAI-compatible inference endpoint. Because Velocity's
inference is model-agnostic (a swappable provider behind one interface), pointing the
whole product — SOP Coach, Executive Intelligence, HR Onboarding, the eval, the UI —
at the provided compute is a **configuration change, not a code change**.

## The three values (Builder Portal → Resources → "Your gateway & key")
- **base_url:** `https://ht.getimpala.ai/v1`
- **model:** `qwen3.6-27b`
- **api_key:** your team's virtual key (`sk-...`) — keep it secret; never commit it.

## Connect (about two minutes)
```bash
export VHOS_LLM_BACKEND=openweights
export VHOS_EMBED_BACKEND=local            # keep offline embeddings; nothing else to provision
export VHOS_OPENWEIGHTS_URL=https://ht.getimpala.ai/v1
export VHOS_OPENWEIGHTS_MODEL=qwen3.6-27b
export VHOS_OPENWEIGHTS_API_KEY=sk-...your-team-key...   # paste yours; do not commit

# 1) prove the model answers through Velocity's agents (grounded + cited):
python scripts/openweights_smoketest.py     # green = the provided model answered

# 2) score the real model on the SOP eval (writes eval/last_report.md):
python eval/run_eval.py

# 3) run the live console on the provided compute:
python ui/server.py                          # badge shows: model qwen3.6-27b
```

## Capture proof (for the logbook + data room)
- Screenshot the **green smoke-test** output (the model's answer + cited SOP source).
- Screenshot the **console badge** reading `backend openweights · model qwen3.6-27b`.
- Save the eval report (`eval/last_report.md`) run against `qwen3.6-27b`.

These are the "running on the provided compute" evidence artifacts — they turn the
model-agnostic claim into something a judge can open.

## Why this is the honest framing
The provided compute is a **managed open-weights gateway** (Impala serving Qwen 3.6
27B), not a raw GPU we self-host. That is still an open-weights model on the
buildathon's provided compute, reached through our provider abstraction. If you later
want fully self-hosted inference (vLLM on your own GPU), the same `openweights`
provider points there too — see `openweights-runbook.md`. No Velocity code changes in
either case; only the three config values above.
