"""1 - HR Onboarding Agent (functional preboarding).

Runs preboarding before arrival: determines the documents required for each hire's
role, flags missing documents and expiring work permits/visas against the start
date, assigns a role-specific training plan, and produces an LLM-synthesized
readiness digest for the HR manager.

Document requests and permit escalations are routed for human approval (they
contact a person); training assignment is internal/low-risk. The digest is
generated via the pluggable LLM backend (Bedrock Claude, with an offline fallback).
"""
from __future__ import annotations

from datetime import date, timedelta

from velocity_hos.llm import LLM, get_llm

from .base import Agent, Context, Recommendation, RiskLevel

BASE_DOCS = ("passport", "work_permit", "contract", "tax_form")

ROLE_DOCS = {
    "f&b": ("food_handler_cert",),
    "kitchen": ("food_handler_cert",),
    "security": ("security_license",),
    "spa": ("practitioner_license",),
}

ROLE_TRAINING = {
    "f&b": ("Brand service standards", "POS/Micros", "Responsible alcohol service"),
    "front office": ("PMS check-in/out", "Upselling", "Guest recovery basics"),
    "housekeeping": ("Turndown SOP", "Chemical safety"),
    "kitchen": ("HACCP food safety", "Kitchen SOPs"),
}
DEFAULT_TRAINING = ("Orientation & culture", "Health & safety", "Code of conduct")

PERMIT_WARN_DAYS = 30


def _match(role: str, table: dict) -> tuple:
    role_l = (role or "").lower()
    for key, val in table.items():
        if key in role_l:
            return val
    return ()


def _parse_date(value) -> date | None:
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


class HROnboardingAgent(Agent):
    name = "hr_onboarding"

    def __init__(self, llm: LLM | None = None, today: date | None = None):
        self._llm = llm or get_llm()
        self._today = today or date.today()

    def evaluate(self, ctx: Context) -> list[Recommendation]:
        recs: list[Recommendation] = []
        sections: dict[str, list[str]] = {
            "missing_documents": [], "permit_or_visa_issues": [],
            "training_assigned": [], "ready_to_start": [],
        }

        for hire in ctx.inputs.get("new_hires", []):
            name = hire.get("name", "New hire")
            role = hire.get("role", "")
            required = list(BASE_DOCS) + list(_match(role, ROLE_DOCS))
            held = set(hire.get("documents", []))
            missing = [d for d in required if d not in held]

            # 1) Missing documents -> request (contacts the hire) -> human approval.
            if missing:
                sections["missing_documents"].append(f"{name} ({role or 'role TBD'}): {', '.join(missing)}")
                recs.append(Recommendation(
                    agent=self.name,
                    summary=f"Request missing documents from {name}: {', '.join(missing)}",
                    risk=RiskLevel.REQUIRES_APPROVAL,
                    proposed_action={"type": "request_documents", "hire_id": hire.get("id"),
                                     "documents": missing},
                    rationale="Preboarding incomplete; documents required before start date.",
                ))

            # 2) Permit/visa expiry vs start date.
            expiry = _parse_date(hire.get("permit_expiry"))
            start = _parse_date(hire.get("start_date"))
            if expiry is not None:
                threshold = (start or self._today) + timedelta(days=PERMIT_WARN_DAYS)
                if expiry <= threshold:
                    sections["permit_or_visa_issues"].append(
                        f"{name}: work permit expires {expiry.isoformat()}")
                    recs.append(Recommendation(
                        agent=self.name,
                        summary=f"Work permit for {name} expires {expiry.isoformat()} — escalate renewal",
                        risk=RiskLevel.REQUIRES_APPROVAL,
                        proposed_action={"type": "escalate_permit", "hire_id": hire.get("id"),
                                         "expiry": expiry.isoformat()},
                        rationale="Permit/visa expires at or near the start date.",
                    ))

            # 3) Training assignment (internal, low-risk).
            training = list(_match(role, ROLE_TRAINING)) or list(DEFAULT_TRAINING)
            sections["training_assigned"].append(f"{name}: {', '.join(training)}")
            recs.append(Recommendation(
                agent=self.name,
                summary=f"Assign onboarding training to {name}",
                risk=RiskLevel.LOW,
                proposed_action={"type": "assign_training", "hire_id": hire.get("id"),
                                 "modules": training},
                rationale="Role-specific preboarding training so the hire arrives ready.",
            ))

            if not missing and (expiry is None or expiry > (start or self._today) + timedelta(days=PERMIT_WARN_DAYS)):
                sections["ready_to_start"].append(name)

        if ctx.inputs.get("new_hires"):
            digest = self._llm.summarize("Onboarding readiness summary for the HR manager.", sections)
            recs.append(Recommendation(
                agent=self.name,
                summary=digest,
                risk=RiskLevel.INFO,
                proposed_action={"type": "onboarding_digest", "tenant": ctx.tenant_id,
                                 "sections": sections},
                rationale="Cross-hire preboarding readiness roll-up for HR.",
            ))
        return recs
