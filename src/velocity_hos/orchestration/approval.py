"""Human-in-the-loop approval gate.

Any recommendation marked REQUIRES_APPROVAL is held here until a human approves
or rejects it. INFO/LOW recommendations pass through (and are still audited).
In production this is backed by AWS Step Functions' callback pattern; the local
implementation uses an in-memory queue for tests and demos.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from velocity_hos.agents.base import Recommendation, RiskLevel


class ApprovalDecision(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    PENDING = "pending"


@dataclass
class PendingApproval:
    recommendation: Recommendation
    decision: ApprovalDecision = ApprovalDecision.PENDING


@dataclass
class ApprovalGate:
    queue: list[PendingApproval] = field(default_factory=list)

    def submit(self, rec: Recommendation) -> ApprovalDecision:
        """Auto-pass safe recs; hold consequential ones for a human."""
        if rec.risk in (RiskLevel.INFO, RiskLevel.LOW):
            return ApprovalDecision.APPROVED
        self.queue.append(PendingApproval(rec))
        return ApprovalDecision.PENDING

    def resolve(self, index: int, decision: ApprovalDecision) -> None:
        self.queue[index].decision = decision
