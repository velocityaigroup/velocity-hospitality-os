"""Inspectable audit trail — the reasoning/decision record for the whole loop.

Every recommendation an agent makes, and every decision the approval gate takes on
it, is recorded here as a structured, timestamped event. This is the artifact a
technical judge (or an auditor, or a GM) opens to answer "why did the system do
that?" — it captures the agent, its rationale, the SOP sources it grounded on, the
risk level, the proposed action, and the human/automatic decision.

It is deliberately dependency-free and JSON-serializable so it can be exported to
the data room, attached to a demo, or written to the per-tenant DynamoDB audit
table in production. The clock is injectable so tests and reproducible demos can
freeze time; production uses the real wall clock.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from velocity_hos.agents.base import Recommendation


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class AuditEvent:
    """One recorded reasoning+decision step, safe to serialize and inspect."""
    seq: int
    ts: str
    tenant: str
    agent: str
    phase: str
    summary: str
    risk: str
    decision: str
    rationale: str = ""
    sources: list[str] = field(default_factory=list)
    action_type: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AuditTrail:
    """An ordered, timestamped, inspectable record of one or more loop cycles."""
    tenant: str = ""
    clock: Callable[[], str] = _utc_now
    events: list[AuditEvent] = field(default_factory=list)

    def record(
        self,
        rec: Recommendation,
        decision: str,
        *,
        tenant: str | None = None,
        phase: str = "operate",
    ) -> AuditEvent:
        event = AuditEvent(
            seq=len(self.events) + 1,
            ts=self.clock(),
            tenant=tenant or self.tenant,
            agent=rec.agent,
            phase=phase,
            summary=rec.summary.splitlines()[0][:200] if rec.summary else "",
            risk=rec.risk.value,
            decision=decision,
            rationale=rec.rationale,
            sources=list(rec.sources),
            action_type=str(rec.proposed_action.get("type", "")),
        )
        self.events.append(event)
        return event

    # --- views -------------------------------------------------------------
    def to_list(self) -> list[dict[str, Any]]:
        """Back-compat flat view (what LoopResult.audit exposed originally)."""
        return [e.to_dict() for e in self.events]

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(
            {"tenant": self.tenant, "event_count": len(self.events),
             "events": [e.to_dict() for e in self.events]},
            indent=indent,
        )

    def to_markdown(self) -> str:
        lines = [
            f"# Velocity Hospitality OS — Decision Trail ({self.tenant or 'tenant'})",
            "",
            f"{len(self.events)} recorded events. Every agent recommendation and the "
            "decision taken on it, with its grounding sources — inspectable end to end.",
            "",
            "| # | time (UTC) | agent | phase | risk | decision | action | sources | summary |",
            "|---|------------|-------|-------|------|----------|--------|---------|---------|",
        ]
        for e in self.events:
            src = ", ".join(e.sources) if e.sources else "—"
            summary = e.summary.replace("|", "\\|")
            lines.append(
                f"| {e.seq} | {e.ts} | {e.agent} | {e.phase} | {e.risk} | "
                f"{e.decision} | {e.action_type or '—'} | {src} | {summary} |"
            )
        return "\n".join(lines)

    def counts(self) -> dict[str, int]:
        """Quick roll-up for reporting: how many held / auto / info this run."""
        out: dict[str, int] = {}
        for e in self.events:
            out[e.decision] = out.get(e.decision, 0) + 1
        return out
