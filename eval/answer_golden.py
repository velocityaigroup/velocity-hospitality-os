"""Golden set for ANSWER faithfulness — model-dependent accuracy.

Unlike the retrieval eval (which is model-independent by design), this set grades
the LANGUAGE MODEL's answer: for a staff question, does the generated answer state
the correct fact from the property's SOP? Each case lists the required fact(s) a
faithful, concise answer must contain. Matching is normalized (case-insensitive,
punctuation/whitespace-insensitive) so "50 ml", "50ml" and "50-ml" all count.

Run against the provided open-weights model (Qwen 3.6 27B / Impala) to get a real
model-quality number; offline it is a near-100% sanity baseline (the offline backend
answers extractively from the SOP).
"""
from __future__ import annotations

# (question, [required_facts]) — a faithful answer must contain ALL required facts.
ANSWER_CASES: list[tuple[str, list[str]]] = [
    ("how much rum goes in a mojito?", ["50ml"]),
    ("what is the target beverage pour cost?", ["18", "22"]),
    ("how quickly must we acknowledge a guest complaint?", ["15"]),
    ("within how many days of a start date do we renew an expiring work permit?", ["30"]),
    ("which certificate does an F&B or kitchen new hire need before their first shift?", ["food handler"]),
    ("who must inspect a room before it is released as ready?", ["supervisor"]),
    ("how quickly should a VIP guest be greeted by name on arrival?", ["10"]),
    ("what is the response SLA for a safety-critical maintenance defect?", ["immediate"]),
    ("what must be completed before confirming a spa treatment?", ["consultation"]),
    ("who signs off an allergen-adapted dish before it is served?", ["chef"]),
    ("when a fire alarm cannot be verified as false, what should staff do?", ["evacuate"]),
    ("what must be verified before posting a charge to a guest's room in the boutique?", ["guest"]),
    ("what is the first priority in any fire or emergency alarm?", ["life"]),
    ("what must be tracked for every scheduled airport transfer?", ["flight"]),
    ("what should the executive morning briefing lead with?", ["decision"]),
    ("what determines a reservation's cancellation charge?", ["rate plan"]),
    ("can the pool open if the water chemistry is out of the safe range?", ["clos"]),
    ("when must internal stock transfers be recorded?", ["movement"]),
]
