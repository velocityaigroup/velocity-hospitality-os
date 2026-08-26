# Demonstration runbook — the one connected journey
**Target: 3–5 minutes live. Rehearse it cold three times.**
**Property: Firefly Estate Bequia** — a real Vincentian property beats synthetic data on every axis.

---

## Before you start

```bash
cd velocity-hospitality-os
python ui/server.py            # http://localhost:8080
```

Then: open the console, pick **Firefly Estate Bequia** in the header, click **Reset demo**.
Nothing else. No network is required — standard library, offline backend, no credentials.

Have the backup video open in a second tab. Do not skip this.

---

## The journey — ten steps, one continuous flow

Each step is a real thing the software does. Nothing here is staged.

| # | Do this | Say this |
|---|---|---|
| 1 | **Dashboard.** Point at the banner and the "0 of 24 operator-confirmed" tile. | "This is a real Vincentian property. Everything the system knows about it is seeded from their own public website, and every single record is tagged unconfirmed until they confirm it. The system shows you that." |
| 2 | Point at **Onboarding in progress** — two hires at 35% and 80%. | "Two new hires in the pipeline at different stages of preboarding." |
| 3 | **SOP Coach** → click *"how much is the estate tour?"* | "A staff member asks a question. The answer comes back with the exact record it came from — FF-503 — and an unconfirmed badge with the source page. Grounded and cited." |
| 4 | Now click *"what is the room rate for a week in March?"* | "**This is the important one.** It refuses — and it tells you *why*: declared gap G1, no published room rates, go and ask the owner. It does not answer from a neighbouring record that happens to mention rates. A system that invents a hotel's policy is worse than no system." |
| 5 | **Operations Loop** → **Run one operations cycle**. | "One cycle. Four supervised agents over one day of this property's operations." |
| 6 | Point at stage 2, at the Work Order rows. | "The work order agent found path lighting out on the steep steps — steps this property flags on its own candour page — and the villa pool pump with the villa occupied. It scored them, gave them owners and SLAs, and **cited the property's own record for each routing decision**." |
| 7 | Point at stage 3. | "Four items are held. Nothing that touches a person, money or guest safety executes without a human. The routine work — a rattling fan, chipped paint — auto-routed and got logged." |
| 8 | Scroll to stage 5 and read one "Awaiting your approval" line aloud. Then scroll up and **Approve** that item. | "Watch the briefing." |
| 9 | Scroll back to stage 5. | "That item just moved out of *Awaiting your approval* and into *Actions taken*. The Executive Intelligence agent re-ran over the new state. That is the loop closing — and it closed because a human decided, not because the system decided." |
| 10 | Stage 4, then stage 6. | "It became an assigned task with a named owner and an SLA. And every step — the recommendation, the record it grounded on, the human decision, the execution — is in the decision trail, timestamped. That is the artifact you open to answer *why did the system do that?*" |

**Close on:** *"Grounded in the property's own knowledge. Refuses what it hasn't been told. Nothing consequential moves without a person. And you can audit every step."*

---

## Between takes

Click **Reset demo**. It clears the cycle, the approvals, the tasks, the trail and the briefing for
that property, and leaves the property's inputs ready to run again. Switching property does not
disturb the other property's state.

---

## If something goes wrong

| Symptom | Do this |
|---|---|
| A card shows a red error box | Press the button again — the console never dies on a failed call. If it repeats, **Reset demo**. |
| The console will not load | `python ui/server.py` again; check `http://localhost:8080/healthz` returns `{"ok": true}`. |
| Fonts look wrong | Google Fonts is the only external asset. It has fallen back to system fonts. Nothing is broken; keep going. |
| Anything else | Cut to the backup video. Do not debug on stage. |

---

## Questions you will be asked

**"Is this just RAG?"**
Retrieval is one agent of four. The others triage, prioritise, assign owners and SLAs, and hold
consequential work for a person. What makes it a system rather than a chatbot is the loop: an event
becomes a recommendation, a human decision, an assigned task, and a line in the GM's briefing — all
of it audited. And the retrieval half is measured, not asserted: 95% retrieval@1 on 62 cases.

**"What happens when it's wrong?"**
This is the strongest answer, so take your time. It refuses. Two different ways: the grounding
guardrail refuses anything the corpus doesn't support, and the declared-gap guard refuses anything
the property has told us it hasn't documented — naming the gap. 100% refusal accuracy on both
evaluation sets. Then show step 4 again.

**"Is Firefly a customer?"**
No, and be quick and clear about it. Firefly is a design-partner conversation. The knowledge you can
see is seeded from their public website and none of it is operator-confirmed — the console says so
in the header and on every answer. No pilot has been paid for and none has been run.

**"Why you?"**
Vincentian, cruise-line and international luxury hospitality operating background, already shipping
AI systems for paying clients on this stack, and the product is shaped by a direct on-site
operational audit rather than a guess.

---

## What NOT to show

- Agents 5–7 (Revenue, Guest Recovery, Workforce Planning). They are stubs and labelled roadmap.
- The integration connectors. They are interfaces, not live connections.
- Any claim that Bedrock is running in production. It was validated on the account; that is the claim.
