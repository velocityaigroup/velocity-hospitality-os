"""Golden evaluation set for the SOP Coach — scored over the full demo KB.

A labelled set of realistic staff questions (natural phrasing, paraphrases, and
department jargon) mapped to the SOP that should answer them, plus deliberately
out-of-scope questions the agent must REFUSE rather than hallucinate policy. This is
what turns "the SOP Coach works" into a measurable, reproducible number.

The knowledge base is the authored Velocity demo KB (`velocity_hos.knowledge`); a
design partner swaps in their own SOPs with no code change and re-runs this to get a
property-specific accuracy figure.
"""
from __future__ import annotations

from velocity_hos.knowledge import demo_retrieval_docs

# The SOP library under test — the full 16-department demo knowledge base.
SOPS: dict[str, str] = demo_retrieval_docs()

# (question, expected_sop_id | None). None == out-of-scope; the agent must refuse.
CASES: list[tuple[str, str | None]] = [
    # --- Front Office ---
    ("how do I check in a VIP guest?", "FO-101"),
    ("a returning guest is arriving, what's the arrival standard?", "FO-101"),
    ("guest wants to check out late, what do we do?", "FO-108"),
    ("can we give a late checkout?", "FO-108"),
    # --- Food & Beverage ---
    ("how much rum goes in a mojito?", "FB-210"),
    ("what's our target pour cost on cocktails?", "FB-210"),
    ("guest wants to upgrade to a premium spirit", "FB-210"),
    ("we double-booked a table, how do we handle it?", "FB-214"),
    # --- Housekeeping ---
    ("who can mark a room as ready?", "HK-301"),
    ("how do we sequence room cleaning when arrivals are waiting?", "HK-301"),
    # --- Human Resources ---
    ("which documents does a new kitchen hire need before starting?", "HR-501"),
    ("when do we renew a work permit that's expiring?", "HR-501"),
    ("when should we capture uniform sizes for a new starter?", "HR-505"),
    # --- Maintenance / Engineering ---
    ("there's a safety-critical defect, how is it triaged?", "MN-401"),
    ("what's the SLA for a guest-impacting repair?", "MN-401"),
    ("how do we run the preventive maintenance cycle?", "ENG-410"),
    # --- Executive ---
    ("what should the morning briefing lead with?", "EX-601"),
    # --- Guest Experience ---
    ("what's the first step when a guest complains?", "GX-201"),
    ("how fast must we acknowledge a complaint?", "GX-201"),
    # --- Security ---
    ("the fire alarm is going off, what do we do?", "SEC-901"),
    ("can we assume it's a false alarm?", "SEC-901"),
    # --- Finance / Retail ---
    ("how do we handle inventory variance at period close?", "FIN-610"),
    ("when do we record internal stock transfers?", "FIN-610"),
    ("what do we verify before charging a purchase to a room?", "RET-1301"),
    # --- Reservations / Events ---
    ("how do we coordinate a large group arrival?", "RES-701"),
    ("how do we handle a VIP birthday?", "EVT-810"),
    # --- Spa / Pools / Transport ---
    ("what do we check before confirming a spa treatment?", "SPA-1001"),
    ("can the pool open if the water chemistry is off?", "POOL-1101"),
    ("the guest's flight is delayed, what happens to the pickup?", "TR-1201"),

    # --- Depth-pass SOPs ---
    ("a guest can't find their luggage, what do we do?", "FO-115"),
    ("we're oversold tonight, how do we relocate a guest?", "FO-120"),
    ("how do we take an in-room dining order?", "FB-220"),
    ("a guest has a nut allergy, how do we handle the food?", "FB-225"),
    ("how do we service an occupied room on a stayover?", "HK-310"),
    ("how does the probation review work?", "HR-510"),
    ("what's the process when an employee leaves?", "HR-515"),
    ("the AC is broken in an occupied room, what do we do?", "MN-410"),
    ("how do we run crisis communication in an incident?", "EX-610"),
    ("how should we respond to an online review?", "GX-210"),
    ("a guest collapsed, what's the medical emergency protocol?", "SEC-905"),
    ("there's an unattended bag in the lobby, what do we do?", "SEC-910"),
    ("the power went out, what's the generator procedure?", "ENG-415"),
    ("a guest is disputing a charge on their bill", "FIN-615"),
    ("how do we manage overbooking and yield?", "RES-710"),
    ("how do we execute a banquet event order?", "EVT-815"),
    ("how is spa equipment sanitised between guests?", "SPA-1005"),
    ("lightning warning — when can the pool reopen?", "POOL-1105"),
    ("how does valet parking handle guest keys?", "TR-1205"),

    # --- Depth pass 2 ---
    ("how do we handle a boutique return or exchange?", "RET-1305"),
    ("how is guest laundry and dry cleaning handled?", "HK-320"),
    ("how do we run the daily revenue and yield review?", "EX-615"),
    ("how do we manage a returning guest's preferences?", "GX-215"),
    ("how do we control legionella in the water systems?", "ENG-420"),
    ("what's our cancellation and no-show policy?", "RES-715"),
    ("how do we cash up and close the bar?", "FB-230"),
    ("how do we book a guest excursion or activity?", "TR-1210"),

    # --- Out-of-scope — must REFUSE (no property SOP covers these) ---
    ("what is the capital of France?", None),
    ("how do I reset my personal email password?", None),
    ("tell me a joke about penguins", None),
    ("what's the weather forecast for tomorrow?", None),
    ("what's the stock price of Marriott today?", None),
    ("write me a poem about the ocean", None),
]
