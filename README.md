# Velocity Hospitality OS

[![CI](https://github.com/velocityaigroup/velocity-hospitality-os/actions/workflows/ci.yml/badge.svg)](https://github.com/velocityaigroup/velocity-hospitality-os/actions/workflows/ci.yml)


**The agentic execution layer for hospitality.** Hotels already have standards — SOPs, brand manuals, training. They fail because those standards aren't *executed* consistently across shifts, departments, seasons, and properties. Velocity deploys a team of supervised AI agents that sit **above** a hotel's existing systems and make sure standards are followed, measured, and improved — automatically, with a human always in control.

> Built for the **Future Caribbean Global AI Buildathon 2026** · Track: Tourism & Transportation · by [Velocity AI Group](https://velocityaigroup.co)

---

## The problem
In today's hotel stack, a system collects information — then a *human* is expected to remember it, communicate it, follow up, and verify it got done. Every one of those layers is a person holding state in their head, and people forget, leave, and get overwhelmed. The cost is measurable: **70–75% annual staff turnover** (~$5K–$10K per replacement), **20–30% beverage inventory leakage**, and a projected **8.6M-worker shortfall by 2035**.

It's an **execution gap, not a documentation gap.** Velocity automates the remember → communicate → follow-up → verify layer.

## How it works — the execution loop
```
Inputs → Agents → Human Approval → Actions → Systems → Reporting → (continuous improvement → Inputs)
```
- **Inputs** — live operational exhaust: PMS events, POS transactions, guest messages, work orders, applications, reviews, schedules.
- **Agents** — interpret inputs against the property's own SOPs and standards.
- **Human Approval** — anything that moves money, staffing, or the guest relationship is routed to a human.
- **Actions → Systems** — approved actions are written back into existing systems.
- **Reporting** — every action becomes an audit trail that feeds the next decision.

## The seven supervised agents
| # | Agent | Role |
|---|-------|------|
| 1 | HR Onboarding | Preboarding, visa/work-permit tracking, document collection, training assignment |
| 2 | SOP Coach | On-demand, role-specific "how do we do this here?" against the property's standards |
| 3 | Workforce Planning | Staffing forecasts, seasonal-peak planning, recruit-timing recommendations |
| 4 | Work Order | Triage + priority scoring + SLA routing for maintenance and guest requests |
| 5 | Revenue | Upsell surfacing, leakage detection, pricing/pour consistency (Beverage Logic Engine) |
| 6 | Guest Recovery | Complaint analysis, recovery actions, follow-up to closure |
| 7 | Executive Intelligence | Daily executive briefing across one or many properties |

**Human-in-the-loop by design:** agents recommend and prepare; people approve. That's what makes it trustworthy enough to run in a real hotel.

> **Working today** — four supervised agents running the full loop, model-agnostic:
> - **SOP Coach** — a RAG pipeline: retrieve relevant SOP excerpts → answer grounded only in them → **cite sources**, and **refuse** (grounding guardrail) when nothing supports the question instead of inventing policy.
> - **HR Onboarding** — determines required documents by role, flags missing docs and expiring permits/visas against the start date, assigns role-specific training, and produces a readiness digest for HR.
> - **Work Order** — triages maintenance and guest-request tickets to a priority, owner, and SLA, **grounded in the property's own maintenance/safety SOPs** — holding anything safety-critical, guest-impacting, or above a cost threshold for **human approval**, and auto-routing routine work.
> - **Executive Intelligence** — synthesizes the GM's daily briefing from the day's risk/staffing/revenue/compliance alerts **and what the other agents did this cycle** (actions taken + items awaiting approval), which is what closes the loop.
>
> Every recommendation and the decision taken on it is written to an inspectable, timestamped **decision trail** (`demo/decision_trail.md` / `.json`) — the artifact you open to answer "why did the system do that?".
>
> Try it: `python ui/server.py` (console at localhost:8080) · `python demo/run_demo.py` (end-to-end loop) · `python eval/run_eval.py` (measured accuracy).

## Multi-property — and honest about what it knows
Every property is its own tenant: its own knowledge base, its own citations, its own declared gaps. Corpora are never merged, so one property's content can never leak into another's answers.

| Property | Corpus | Provenance |
|---|---|---|
| **Azure Bay Resort** | 46 authored SOPs · 16 departments | Original content written by Velocity to international luxury standards. Operational figures illustrative. |
| **Firefly Estate Bequia** *(Saint Vincent & the Grenadines)* | 24 records · 9 departments · **11 declared knowledge gaps** | **Seeded from the property's own public website. Not a live or paid pilot, and not operator-confirmed** — every record is tagged `unconfirmed` with its source page. |

Two guardrails, not one:
- **Grounding guardrail** — refuses when no record supports the question.
- **Declared-gap guard** — when a property tells us a subject is undocumented (rates, service times, transfer prices), the assistant refuses **by name** — *"no published room rates, please check with the owner/manager"* — instead of answering from a neighbouring record that shares vocabulary. A fact is never promoted to `operator_confirmed` without the operator.

Measured separately, because they are different corpora:

| | Cases | Retrieval@1 | Grounding / gap refusal | Out-of-scope refusal |
|---|---|---|---|---|
| Azure Bay (`eval/run_eval.py`) | 62 | **95%** | **100%** | **100%** |
| Firefly seed (`eval/firefly_eval.py`) | 38 | **100%** | **100%** | **100%** |

*The Firefly figure is on a 38-case public-source seed and is not comparable to the 62-case authored corpus.*

## The console
`python ui/server.py` → http://localhost:8080. Seven views (Dashboard · SOP Coach · Operations Loop · Approvals · Knowledge Base · Knowledge Gaps · Evidence), a property switcher, and a one-click demo reset.

Everything is computed server-side by the same agents the tests and the evaluation run against — there is no client-side copy of the product. **Approvals are real**: approving a held item writes the human decision and the execution to the audit trail, creates an assigned task with an owner and an SLA, and re-runs Executive Intelligence so the item moves out of *Awaiting your approval* and into *Actions taken* in the GM briefing. That is the loop closing, in front of you.

It runs offline — standard library only, no network, no credentials — so it is its own demo fallback. See [`docs/DEMO_RUNBOOK.md`](docs/DEMO_RUNBOOK.md) and [`docs/AUDIT_2026-08-20.md`](docs/AUDIT_2026-08-20.md).

## Model-agnostic & self-hosted
The LLM is a **swappable provider behind one interface** — all retrieval, grounding, citations, evaluation and workflow logic are model-independent. Switch models with a single env var; no application code changes.

| Provider | Status | Use |
|---|---|---|
| **Provided open weights (Impala gateway)** | ✅ **primary** | The buildathon's provided compute — **Qwen 3.6 27B** served over an OpenAI-compatible gateway, reached through our `openweights` provider (config change, no code change). No vendor lock-in. |
| **Amazon Bedrock (Converse)** | ✅ available | Managed cloud provider via the **Converse API** — validated on **Amazon Nova** today. Converse is foundation-model agnostic, so any other foundation model drops in with no code change. |
| **Self-hosted open weights (vLLM)** | ⬚ alternative | The same `openweights` provider can point at a vLLM server on our own GPU for full-sovereignty deployments — no application code change. |
| Offline deterministic | ✅ | Hermetic default for CI/tests — no network. |
| Other AI providers (direct APIs) | ⬚ addable | Same interface — add without touching app logic. |

By design there is **no hard dependency on any single model vendor** — the foundation model is swapped with one env var. *(Some managed foundation models are entitlement-gated on our AWS account; because Bedrock uses Converse and the backend is provider-agnostic, we run an available model — Amazon Nova — or self-hosted open weights instead, with nothing blocked.)* See [`docs/openweights-runbook.md`](docs/openweights-runbook.md), [`docs/bedrock-deploy.md`](docs/bedrock-deploy.md), [`docs/model-benchmark.md`](docs/model-benchmark.md) and [`docs/architecture-model-agnostic.svg`](docs/architecture-model-agnostic.svg).

## Architecture
- **AI provider (pluggable)** — open-weights self-hosted (official) · offline · Bedrock Converse + other providers optional
- **Model-independent core** — RAG retrieval, grounding guardrail, citations, evaluation harness
- **Orchestration** — the execution loop + human-in-the-loop approval gate (AWS Step Functions + Lambda in production)
- **State** — DynamoDB, per-tenant isolation · **Integrations** — PMS, POS/Micros, SevenRooms, payroll via REST/webhooks

Security & trust are first-class: least-privilege access, multi-property tenant isolation, full auditability, transparency by design.

## Buildathon scope (21-day sprint)
- A working agentic core: **≥3 of the 7 agents** (HR Onboarding, SOP Coach, Executive Intelligence) running the full loop on AWS
- A clickable product demo + deployed architecture
- A Caribbean pilot roadmap with ≥1 design-partner conversation advancing toward an LOI

## Repo structure
```
src/velocity_hos/
  agents/          # the seven agent definitions (base + 7 agents; SOP Coach = RAG)
  orchestration/   # execution loop + human-in-the-loop approval gate
  integrations/    # PMS, POS, payroll connectors
  llm/             # provider abstraction: local · openweights (vLLM) · bedrock
  rag/             # chunking, vector store, retriever, grounding guardrail
  data/            # model-independent SOP knowledge seed
  knowledge/       # per-property corpora + registry (authored demo · Firefly seed + gaps)
ui/                # dependency-free live console (server.py) — 7 views, multi-property
eval/              # evaluation harnesses + golden sets (one per property corpus)
scripts/           # bedrock / open-weights smoke tests
infra/             # AWS SAM (Lambda, API Gateway, DynamoDB)
demo/              # end-to-end hero-loop demo
docs/              # architecture (model-agnostic), agentic loop, RAG, runbooks
tests/             # pytest suite (loop, approval, SOP Coach, eval, providers)
```

## Quickstart
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest                                            # 69 tests, offline, ~6s
ruff check .
python eval/run_eval.py                           # authored corpus  — 95% / 100% / 100%
python eval/firefly_eval.py                       # Firefly seed     — 100% / 100% / 100%
python demo/run_demo.py --property firefly-bequia # end-to-end loop, four agents
python ui/server.py                               # console at localhost:8080
```

## Status
Velocity AI Group already ships production AI systems on this AWS stack for paying clients across the UK and the Caribbean — the architecture is proven, not theoretical. Product shaped by a direct on-site operational audit (HR workflow analysis, management interviews, workforce/onboarding mapping).

## Team
**Druvaughn Edwards** — Founder, Velocity AI Group. Vincentian; cruise-line and international luxury hospitality operating background; ships AI automation systems today.

## License
[MIT](LICENSE) — permissive open source, in keeping with the buildathon's open-source emphasis.
