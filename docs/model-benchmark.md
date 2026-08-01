# Foundation-model benchmark — choosing the buildathon model

Velocity is provider-agnostic; this documents *which foundation model we run and why*,
and how to reproduce the comparison. Run `eval/bench_models.py` against any model and it
reports the signals that matter for our hospitality use cases.

## What we measure (and why these)
| Signal | Why it matters here |
|---|---|
| **Faithfulness** (grounded recall) | The SOP Coach must reproduce the property's standard accurately. We measure how much of the retrieved SOP's key content survives into the answer. |
| **Latency** | The live demo and floor-staff use are interactive — answer speed is user experience. |
| **Refusal accuracy** | Out-of-scope questions must be declined, not hallucinated. (Model-independent — our guardrail owns this — but reported for completeness.) |
| **Conciseness** | Floor staff want a short, correct answer, not an essay. |

> Correctness is carried largely by the **model-independent core** (retrieval + grounding
> guardrail + citations). The foundation model's job is to phrase the retrieved SOP
> faithfully and briefly. That means a **smaller, faster model is often the right call** —
> the heavy lifting isn't the model's.

## How to run (fill this table)
```bash
VHOS_LLM_BACKEND=bedrock VHOS_EMBED_BACKEND=local \
  BEDROCK_MODEL_ID=amazon.nova-lite-v1:0 python eval/bench_models.py --label nova-lite
VHOS_LLM_BACKEND=bedrock VHOS_EMBED_BACKEND=local \
  BEDROCK_MODEL_ID=amazon.nova-pro-v1:0  python eval/bench_models.py --label nova-pro
python eval/bench_models.py --compare
```

| Model | Faithfulness¹ | Latency (ms) | Refusal | Avg chars | Notes |
|---|---|---|---|---|---|
| **Nova Lite** (`amazon.nova-lite-v1:0`) | **0.55** | **~1198** | **1.00** | **172** | measured 2026-08-01 · live on AWS |
| Nova Pro (`amazon.nova-pro-v1:0`) | 0.48 | ~1245 | 1.00 | 119 | measured 2026-08-01 · no gain vs Lite |
| *(offline proof)* | 1.00 | ~0.4 | 1.00 | 196 | deterministic baseline |

**Measured verdict (2026-08-01): Nova Lite wins — decision confirmed by data.** Head to head
on our hospitality set, Nova Pro showed **no advantage**: identical refusal accuracy (1.00),
essentially the same latency (Pro ~47ms *slower*), and Pro was actually *terser* (119 vs 172
chars → lower token recall, not higher). Since Pro costs more for zero measurable quality gain
on this grounded/extractive task, **Nova Lite is the default managed model.** (Faithfulness is
recall-based, so it does not capture a correctness gap; both models cited the correct source
and refused every out-of-scope question in the run, and spot-checked answers were correct.)

> ¹ **Reading faithfulness correctly.** This metric is *recall of the retrieved SOP's key
> tokens in the answer* — so a **concise, correct** answer scores below 1.0 by design. Nova
> Lite answered *"a mojito requires 50ml of white rum"* — correct and cited (`bev.mojito`),
> but it doesn't recite the mint/lime/sugar/soda, so recall ≈ 0.55. That is **desired**
> behaviour for floor-staff Q&A (answer the question, don't lecture). The load-bearing
> quality signals are: **refusal accuracy 1.00** (no hallucination on out-of-scope) and
> **correct source citation** (verified in the smoke test). Use Pro's number only to check
> whether it materially improves *correctness*, not verbosity.

## Recommendation (default: Nova Lite)
For the buildathon we default to **Amazon Nova Lite** as the managed provider, for three
reasons:
1. **The task is grounded and extractive.** Answers must restate a retrieved SOP, not
   reason from scratch. A smaller model does this faithfully; the grounding guardrail and
   citations — not the model — guarantee correctness.
2. **Latency is UX.** Nova Lite's low latency keeps the live demo and floor use snappy.
3. **Cost/scale.** A per-property SaaS that runs many queries wants the cheapest model that
   clears the quality bar — better unit economics, a defensibility point for investors.

**Escalate to Nova Pro** *only if* the benchmark shows a real faithfulness/quality gap on
the hospitality cases (e.g., Pro's faithfulness materially exceeds Lite's on the briefing/
multi-fact answers). Because switching is a **config change** (`BEDROCK_MODEL_ID`), we can
adopt Pro — or a self-hosted open-weights model, or any future model — with zero code
change. The official production path remains **self-hosted open weights (Qwen3.6-27B) on
the H200**; Nova is the validated managed alternative.

> Honesty: the offline row is a deterministic baseline, not a model score. Fill the Nova
> rows by running the commands above on the account; do not quote model numbers until measured.
