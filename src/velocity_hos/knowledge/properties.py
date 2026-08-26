"""Property registry — one tenant, one knowledge base, one set of citations.

Velocity is multi-property by design: every property carries its own SOP corpus,
its own declared knowledge gaps, its own departments and its own operational inputs.
Nothing is shared between them, so a citation always belongs to exactly one property
and one property's content can never leak into another's answers.

Two properties are registered:

* ``azure-bay``      — the authored demonstration resort. 46 SOPs across 16
                       departments, written by Velocity to international luxury
                       standards. This is the corpus the published evaluation
                       (95% retrieval@1 / 100% grounding / 100% refusal) runs on.
* ``firefly-bequia`` — Firefly Estate Bequia, the featured design-partner property in
                       Saint Vincent & the Grenadines. Its corpus is a SEED built
                       from the property's own public website; every record is tagged
                       ``unconfirmed`` until the operator confirms it, and the
                       subjects the public web cannot answer are declared as gaps so
                       the assistant refuses them by name.

Operational inputs are generated RELATIVE TO TODAY so a demonstration never shows a
stale date, and so "expires in 12 days" is true on the day it is shown.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Callable

from .corpus import DEMO_SOPS
from .evidence import FINDINGS
from .firefly import FIREFLY_GAPS, FIREFLY_SOPS, SOURCE_PAGES
from .schema import SOP, retrieval_docs


@dataclass(frozen=True)
class Property:
    """One tenant: its identity, its knowledge, and the day's operational inputs."""
    key: str
    tenant_id: str
    name: str
    subtitle: str
    location: str
    kind: str                       # "demonstration" | "design-partner seed"
    provenance: str                 # the honesty line shown in the console header
    sops: list[SOP]
    gaps: list[dict] = field(default_factory=list)
    sample_questions: list[str] = field(default_factory=list)
    refusal_questions: list[str] = field(default_factory=list)
    team: list[dict] = field(default_factory=list)
    _inputs: Callable[[date], dict[str, Any]] | None = None

    # ------------------------------------------------------------------ knowledge
    def retrieval_docs(self) -> dict[str, str]:
        return retrieval_docs(self.sops)

    def departments(self) -> list[str]:
        seen: list[str] = []
        for s in self.sops:
            if s.department not in seen:
                seen.append(s.department)
        return seen

    def provenance_counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for s in self.sops:
            out[s.confidence] = out.get(s.confidence, 0) + 1
        return out

    # ------------------------------------------------------------------- inputs
    def inputs(self, today: date | None = None) -> dict[str, Any]:
        """The property's operational exhaust for one day, relative to ``today``."""
        base = self._inputs(today or date.today()) if self._inputs else {}
        # The declared gaps travel with the inputs so the SOP Coach can refuse by name.
        return {**base, "known_gaps": self.gaps}


# =============================================================================
# Azure Bay Resort — the authored demonstration property
# =============================================================================
def _azure_bay_inputs(today: date) -> dict[str, Any]:
    return {
        "question": "how much rum goes in a mojito?",
        "new_hires": [
            {"id": "H-101", "name": "Ana P.", "role": "f&b",
             "documents": ["passport", "contract", "tax_form"],
             "permit_expiry": (today + timedelta(days=12)).isoformat(),
             "start_date": (today + timedelta(days=6)).isoformat(),
             "onboarding_progress": 40},
            {"id": "H-102", "name": "Marko D.", "role": "front office",
             "documents": ["passport", "work_permit", "contract", "tax_form"],
             "start_date": (today + timedelta(days=9)).isoformat(),
             "onboarding_progress": 85},
        ],
        "tickets": [
            {"id": "WO-501", "category": "safety",
             "description": "elevator 2 stalling intermittently between floors",
             "reported": (today - timedelta(days=1)).isoformat()},
            {"id": "WO-502", "category": "vip",
             "description": "suite 610 AC not cooling, VIP guest in house",
             "reported": today.isoformat()},
            {"id": "WO-503", "category": "comfort",
             "description": "lobby restroom tap dripping",
             "reported": today.isoformat()},
            {"id": "WO-504", "category": "cosmetic",
             "description": "scuff mark on the floor 3 corridor wall",
             "reported": (today - timedelta(days=2)).isoformat()},
        ],
        "signals": {
            "risks": ["Storm warning Thursday PM — pool & watersports"],
            "staffing_alerts": ["F&B short 2 covers for Friday peak"],
            "revenue_alerts": ["Cabanas unbooked for the weekend (premium inventory idle)"],
            "compliance_alerts": ["1 work permit expiring within 30 days"],
        },
        "kpis": [
            {"label": "Occupancy", "value": "82", "unit": "%", "delta": "+7% vs yesterday"},
            {"label": "RevPAR", "value": "312", "unit": "€", "delta": "+12% vs yesterday"},
            {"label": "ADR", "value": "381", "unit": "€", "delta": "+9% vs yesterday"},
            {"label": "Guest satisfaction", "value": "4.8", "unit": "/5", "delta": "+0.3 vs yesterday"},
        ],
        "open_items": [
            {"kind": "risk", "label": "Safety", "text": "Work-order triage — 2 open"},
            {"kind": "await", "label": "Arrivals", "text": "3 VIP arrivals today"},
            {"kind": "info", "label": "Compliance", "text": "1 work permit expiring < 30 days"},
            {"kind": "ok", "label": "In house", "text": "156 in-house · 24 arrivals · 18 departures"},
        ],
    }


AZURE_BAY = Property(
    key="azure-bay",
    tenant_id="azure-bay-demo",
    name="Azure Bay Resort",
    subtitle="Demonstration property",
    location="Adriatic · 210 keys",
    kind="demonstration",
    provenance=("Authored demonstration corpus — original SOPs written by Velocity to "
                "international luxury standards. Operational figures are illustrative."),
    sops=DEMO_SOPS,
    gaps=[],
    sample_questions=[
        "how much rum goes in a mojito?",
        "which documents does a new kitchen hire need?",
        "a guest collapsed, what's the medical emergency protocol?",
        "the power went out, what's the generator procedure?",
        "how do we service an occupied room on a stayover?",
    ],
    refusal_questions=["what is the capital of France?"],
    team=[
        {"name": "Elena V.", "role": "General Manager", "department": "Executive Operations"},
        {"name": "Tomas R.", "role": "Front Office Manager", "department": "Front Office"},
        {"name": "Ana P.", "role": "Bartender (new hire)", "department": "Food & Beverage"},
        {"name": "Marko D.", "role": "Receptionist (new hire)", "department": "Front Office"},
    ],
    _inputs=_azure_bay_inputs,
)


# =============================================================================
# Firefly Estate Bequia — the featured design-partner property
# =============================================================================
def _firefly_inputs(today: date) -> dict[str, Any]:
    return {
        "question": "how much is the estate tour and when does it run?",
        "new_hires": [
            # Mid-onboarding: missing documents, and a certificate expiring near the start date.
            {"id": "FF-H-01", "name": "Shanice B.", "role": "f&b",
             "documents": ["passport", "contract"],
             "permit_expiry": (today + timedelta(days=21)).isoformat(),
             "start_date": (today + timedelta(days=7)).isoformat(),
             "onboarding_progress": 35},
            # Nearly ready: everything in, training outstanding only.
            {"id": "FF-H-02", "name": "Kemron J.", "role": "housekeeping",
             "documents": ["passport", "work_permit", "contract", "tax_form"],
             "start_date": (today + timedelta(days=14)).isoformat(),
             "onboarding_progress": 80},
        ],
        "tickets": [
            {"id": "FF-WO-01", "category": "safety",
             "description": "path lighting out on the steep steps between the rooms and the pool",
             "reported": (today - timedelta(days=1)).isoformat()},
            {"id": "FF-WO-02", "category": "vip",
             "description": "Paradise Beach Villa pool pump noisy, four-bedroom villa occupied",
             "reported": today.isoformat()},
            {"id": "FF-WO-03", "category": "comfort",
             "description": "ceiling fan rattling in Nutmeg",
             "reported": today.isoformat()},
            {"id": "FF-WO-04", "category": "cosmetic",
             "description": "paint chipped on the estate cottage balcony rail",
             "reported": (today - timedelta(days=3)).isoformat()},
        ],
        "signals": {
            "risks": [
                "Steep-step path lighting out — the property's own candour page flags these steps",
            ],
            "staffing_alerts": [
                "One person covering rooms, restaurant, tours and golf enquiries on a single WhatsApp line",
            ],
            "revenue_alerts": [
                "Estate tour has open 11.00am and 2.00pm slots this week (EC$15 per person)",
                "Golf tee sheet empty Thursday and Friday (EC$50 per person)",
            ],
            "compliance_alerts": [
                "Food handler certificate outstanding for a new F&B hire starting in 7 days",
            ],
        },
        "kpis": [
            {"label": "Rooms", "value": "4", "unit": "", "delta": "+ cottage + beach villa"},
            {"label": "Enquiry channels", "value": "1", "unit": "", "delta": "WhatsApp + email, all revenue lines"},
            {"label": "Knowledge records", "value": str(len(FIREFLY_SOPS)), "unit": "",
             "delta": "seeded from public sources"},
            {"label": "Operator-confirmed", "value": "0",
             "unit": f"/{len(FIREFLY_SOPS)}", "delta": "awaiting Firefly"},
        ],
        "open_items": [
            {"kind": "risk", "label": "Safety", "text": "Path lighting out on the steep steps"},
            {"kind": "await", "label": "Villa", "text": "Beach Villa pool pump — villa occupied"},
            {"kind": "info", "label": "Knowledge", "text": f"{len(FIREFLY_GAPS)} declared gaps awaiting operator input"},
            {"kind": "info", "label": "Provenance", "text": f"0 of {len(FIREFLY_SOPS)} records operator-confirmed"},
        ],
    }


FIREFLY = Property(
    key="firefly-bequia",
    tenant_id="firefly-bequia",
    name="Firefly Estate Bequia",
    subtitle="Design-partner property (seed)",
    location="Spring Valley, Bequia · Saint Vincent & the Grenadines",
    kind="design-partner seed",
    provenance=("Seeded from Firefly's own public website. NOT a live or paid pilot, and "
                "not operator-confirmed: every record is tagged unconfirmed with its "
                "source page, and the subjects the public web cannot answer are declared "
                "as gaps the assistant refuses by name."),
    sops=FIREFLY_SOPS,
    gaps=[{**g, "owner": "the owner/manager"} for g in FIREFLY_GAPS],
    sample_questions=[
        "how much is the estate tour?",
        "how much does golf cost and are clubs included?",
        "is laundry included in the room?",
        "is there a ferry from Barbados?",
        "who runs the diving?",
        "does the villa have a private pool?",
    ],
    refusal_questions=[
        "what is the room rate for a week in March?",
        "what time is dinner served?",
        "what time can I check in?",
        "how much is a taxi from the airport?",
    ],
    team=[
        {"name": "Owner / Manager", "role": "Owner-manager", "department": "Staff Operations"},
        {"name": "Shanice B.", "role": "Restaurant & bar (new hire)", "department": "Food & Beverage"},
        {"name": "Kemron J.", "role": "Housekeeping (new hire)", "department": "Accommodation"},
        {"name": "Estate team", "role": "Grounds, tours & golf", "department": "Activities & Golf"},
    ],
    _inputs=_firefly_inputs,
)


PROPERTIES: dict[str, Property] = {p.key: p for p in (AZURE_BAY, FIREFLY)}
DEFAULT_PROPERTY = AZURE_BAY.key


def get_property(key: str | None) -> Property:
    """Look up a property by key, falling back to the default demonstration property."""
    return PROPERTIES.get(key or DEFAULT_PROPERTY, PROPERTIES[DEFAULT_PROPERTY])


def property_index() -> list[dict[str, Any]]:
    """Lightweight list for the console's property switcher."""
    return [
        {"key": p.key, "name": p.name, "subtitle": p.subtitle, "location": p.location,
         "kind": p.kind, "sops": len(p.sops), "departments": len(p.departments()),
         "gaps": len(p.gaps), "provenance": p.provenance,
         "provenance_counts": p.provenance_counts()}
        for p in PROPERTIES.values()
    ]


__all__ = [
    "Property", "PROPERTIES", "DEFAULT_PROPERTY", "AZURE_BAY", "FIREFLY",
    "get_property", "property_index", "FINDINGS", "SOURCE_PAGES",
]
