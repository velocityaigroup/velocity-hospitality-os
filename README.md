# Velocity Hospitality OS

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

## Architecture
Cloud-native on **AWS**:
- **Amazon Bedrock** — agent reasoning
- **AWS Step Functions + Lambda** — orchestration and the execution loop
- **API Gateway + DynamoDB** — serverless backbone with per-tenant isolation
- **Vector store (RAG)** — SOP/knowledge retrieval
- Integration layer — PMS, POS/Micros, SevenRooms, payroll via REST/webhooks

Security & trust are first-class: least-privilege access, multi-property tenant isolation, full auditability, transparency by design.

## Buildathon scope (21-day sprint)
- A working agentic core: **≥3 of the 7 agents** (HR Onboarding, SOP Coach, Executive Intelligence) running the full loop on AWS
- A clickable product demo + deployed architecture
- A Caribbean pilot roadmap with ≥1 design-partner conversation advancing toward an LOI

## Repo structure (planned)
```
/agents          # the seven agent definitions + prompts
/orchestration   # Step Functions / loop logic
/integrations    # PMS, POS, payroll connectors
/infra           # AWS IaC (Lambda, API Gateway, DynamoDB)
/demo            # clickable product demo
/docs            # architecture, diagrams, decision records
```

## Status
Velocity AI Group already ships production AI systems on this AWS stack for paying clients across the UK and the Caribbean — the architecture is proven, not theoretical. Product shaped by a direct on-site operational audit (HR workflow analysis, management interviews, workforce/onboarding mapping).

## Team
**Druvaughn Edwards** — Founder, Velocity AI Group. Vincentian; cruise-line and international luxury hospitality operating background; ships AI automation systems today.

## License
`[Choose — e.g. MIT or Apache-2.0. The buildathon emphasizes open-source agentic systems, so a permissive OSS license is recommended.]`
