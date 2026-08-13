"""Evidence base — the operational findings Velocity Hospitality OS is built on.

Every capability traces to a documented operational finding from primary research:
a direct on-site operational audit of a luxury Adriatic resort plus cross-property
operator interviews. Findings here are ANONYMIZED and abstracted — no property is
named and no proprietary document is reproduced; these are the product-facing
patterns, with each source's validation strength preserved so the record stays
honest (a pattern seen at ≥2 independent properties is far stronger than a single
observation).

This is what lets a hotel executive say "yes, that is exactly our reality," and what
lets a judge see the product solves real, evidenced problems — not imagined ones.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Finding:
    fid: str                       # e.g. "E1"
    theme: str
    observation: str               # the abstracted, anonymized operational pain
    business_impact: str
    validation: str                # "validated" | "reported" | "single-observation"
    sources: str                   # abstracted provenance
    addressed_by: list[str] = field(default_factory=list)  # capabilities/SOPs
    status: str = "live"           # live | roadmap


# Abstracted from a structured operational-audit database (23 logged pain points
# across 10 themes). Numbers are as-observed / illustrative, never presented as
# guarantees.
FINDINGS: list[Finding] = [
    Finding(
        "E1", "Knowledge locked in people, not systems",
        "Procedural knowledge lives in managers' heads; the same questions "
        "(how to void a check, where equipment is, who to contact, timings) are "
        "asked repeatedly — on the order of ~100 procedural questions a day reaching "
        "managers at one property.",
        "Managers act as a human help desk; hours/day of senior time absorbed; slow, "
        "inconsistent answers on the floor.",
        "validated", "on-site audit + operator interview (2 independent properties)",
        ["SOP Coach (Knowledge Assistant)"], "live",
    ),
    Finding(
        "E2", "SOPs stale, not location-specific, rarely opened",
        "Standard operating procedures exist but are outdated, generic across sites, "
        "and so rarely trusted that staff revert to asking a manager instead.",
        "The content exists but the access gap is the real bottleneck; standards "
        "don't get executed consistently.",
        "validated", "on-site audit + operator interview (2 independent properties)",
        ["SOP Coach grounding + citations", "Demo Knowledge Base"], "live",
    ),
    Finding(
        "E3", "Onboarding is slow and unstructured",
        "No pre-arrival preparation; new hires arrive to unexplained logistics "
        "(accommodation, tax ID, uniform, facilities). Time-to-productivity observed "
        "at ~15–30 days for a bartender.",
        "Weeks of sub-productive labour per hire; acute with seasonal churn; poor "
        "first impression; manager time absorbed orienting new staff.",
        "reported", "on-site audit + F&B operator interview",
        ["HR Onboarding agent"], "live",
    ),
    Finding(
        "E4", "Reporting and planning are manual",
        "Daily, weekly, and department reports are hand-assembled by managers; an "
        "operator explicitly asked for automated head-of-department reports.",
        "Recurring manager admin hours that add no operational value.",
        "validated", "on-site audit + operator interview (2 properties)",
        ["Executive Intelligence briefing"], "live",
    ),
    Finding(
        "E5", "Maintenance lacks urgency scoring / triage",
        "A defect becomes a ticket, is then re-posted to a chat group with photos, and "
        "management validates urgency on every ticket by hand before it is prioritised.",
        "Duplicate communication, a management bottleneck on triage, and delayed "
        "response with asset and guest-experience cost.",
        "reported", "on-site audit (single property)",
        ["Work Order triage & SLA routing SOP (MN-401)", "Work Order agent"], "roadmap",
    ),
    Finding(
        "E6", "Operational comms scattered across chat groups",
        "Chat groups are the de-facto operations backbone; information is scattered, "
        "duplicated, and missed, with no system of record and no read confirmation.",
        "Errors and rework from missed updates; no accountability that a message was seen.",
        "reported", "on-site audit (single property, repeatedly observed)",
        ["Communication Center"], "roadmap",
    ),
    Finding(
        "E7", "Premium revenue assets allocated manually",
        "Cabanas, daybeds, and VIP spaces are managed by walk-ups, phone calls, staff "
        "memory, and paper lists, with no occupancy, revenue-per-asset, or no-show "
        "analytics.",
        "Lost bookings and upsell revenue, double-bookings, inconsistent upselling, and "
        "zero visibility into premium-inventory performance.",
        "single-observation", "on-site beach observation (single property) — unvalidated",
        ["Pool & Beach / cabana SOP (POOL-1101)", "Premium Inventory module"], "roadmap",
    ),
]


def live_findings() -> list[Finding]:
    return [f for f in FINDINGS if f.status == "live"]


def evidence_summary() -> dict[str, int]:
    return {
        "findings": len(FINDINGS),
        "validated": sum(f.validation == "validated" for f in FINDINGS),
        "addressed_live": len(live_findings()),
    }
