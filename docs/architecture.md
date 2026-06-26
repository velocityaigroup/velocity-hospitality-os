# Architecture

Velocity Hospitality OS is cloud-native on **AWS** and deliberately sits *above*
the existing hotel stack rather than replacing it.

## Components
| Layer | AWS service | Role |
|-------|-------------|------|
| Reasoning | Amazon Bedrock | Agent reasoning / LLM calls |
| Orchestration | Step Functions + Lambda | The execution loop, approval callbacks |
| State & audit | DynamoDB | Per-tenant state + immutable audit trail |
| API | API Gateway | Ingest signals, serve approvals UI/webhooks |
| Knowledge | Vector store (RAG) | SOP / standards retrieval |
| Integrations | REST / webhooks | PMS, POS/Micros, SevenRooms, payroll |

## The execution loop
```
Inputs -> Agents -> Human Approval -> Actions -> Systems -> Reporting
   ^                                                            |
   +------------------ continuous improvement ------------------+
```
See `agentic-loop.md` and `workflow-diagram.png`.

## Trust & security
- Least-privilege IAM; per-tenant isolation for multi-property groups.
- Full auditability: every agent decision and action is logged (DynamoDB audit table).
- Human-in-the-loop: anything touching money, staffing, or the guest relationship
  is gated behind explicit human approval (Step Functions callback pattern).
