"""Seed SOP library — generic, sanitized hospitality standards.

This is the property "knowledge" the SOP Coach retrieves over. It is deliberately
model-independent: the same grounding, citation and evaluation logic runs whatever
LLM backend is active. Replace these with a design partner's real SOPs to get
property-specific answers — no code changes required.
"""
from __future__ import annotations

SEED_SOPS: dict[str, str] = {
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
