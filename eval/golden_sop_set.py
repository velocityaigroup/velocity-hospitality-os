"""Golden evaluation set for the SOP Coach.

A labelled set of staff questions mapped to the SOP that should answer them, plus
deliberately out-of-scope questions the agent must REFUSE. This is what turns
"the SOP Coach works" into a measurable number. SOP text here is generic and
sanitized (no real property data); replace with a design partner's own SOPs to
report property-specific accuracy.
"""
from __future__ import annotations

# --- Property SOP library (generic / sanitized) -------------------------------
SOPS: dict[str, str] = {
    "bev.mojito": (
        "Mojito spec: 50ml white rum, 8 mint leaves, 25ml lime juice, 2 tsp sugar, "
        "top with soda. Always free-pour with a jigger; never eyeball the rum."
    ),
    "bev.pour_cost": (
        "Beverage pour cost: every cocktail is measured with a jigger. Target pour "
        "cost is 18-22 percent. Bartenders log spills and comps; unlogged variance "
        "over 5 percent is escalated to the bar manager."
    ),
    "fo.checkin": (
        "Front office check-in: greet the guest within 10 seconds, verify ID and "
        "reservation, offer a welcome drink, confirm departure date, and escort VIP "
        "guests to their room."
    ),
    "hk.turndown": (
        "Housekeeping turndown begins at 6pm: lower the blinds, dim the lights, "
        "place water and chocolate, and fold the bed corner."
    ),
    "hr.permit": (
        "Work permits and visas must be valid through the contract period. HR "
        "escalates any permit expiring within 30 days of a start date and begins "
        "renewal before onboarding completes."
    ),
    "hr.onboarding_docs": (
        "New hire documents required before start: passport, work permit, signed "
        "contract, and tax form. F&B and kitchen roles also require a valid food "
        "handler certificate before their first shift."
    ),
    "rev.cabana": (
        "Cabanas and day beds are bookable premium inventory. Reserve via the pool "
        "host, capture the guest room or a day-pass payment, and record the booking "
        "so the space is never given away for free."
    ),
    "guest.recovery": (
        "Guest complaint recovery: acknowledge within 15 minutes, log the issue, "
        "offer a service-recovery gesture within the duty manager's authority, and "
        "follow up before departure to confirm the guest is satisfied."
    ),
}

# --- Labelled cases -----------------------------------------------------------
# (question, expected_doc_id | None). None == out-of-scope; agent must refuse.
CASES: list[tuple[str, str | None]] = [
    # In-scope — should answer and cite the right SOP
    ("how much rum goes in a mojito?", "bev.mojito"),
    ("what's our target pour cost on cocktails?", "bev.pour_cost"),
    ("how do I check in a VIP guest?", "fo.checkin"),
    ("what time does turndown service start?", "hk.turndown"),
    ("when do we renew a work permit that's expiring?", "hr.permit"),
    ("which documents does a new kitchen hire need before starting?", "hr.onboarding_docs"),
    ("how do we handle a cabana booking at the pool?", "rev.cabana"),
    ("what's the first step when a guest complains?", "guest.recovery"),
    # Out-of-scope — should REFUSE (no property SOP covers these)
    ("what is the capital of France?", None),
    ("how do I reset my personal email password?", None),
    ("tell me a joke about penguins", None),
    ("what's the weather forecast for tomorrow?", None),
]
