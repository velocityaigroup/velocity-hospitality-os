"""Velocity Hospitality OS — live operations console (dependency-free).

    python ui/server.py         # then open http://localhost:8080

Everything on this console is computed server-side by the SAME Python agents,
hybrid retrieval, grounding guardrail and human-approval gate used in the tests,
the evaluation harness and the demo — served live, not mocked. There is no
client-side copy of the product.

It is multi-property: switch between the authored demonstration resort and the
featured design-partner property (Firefly Estate Bequia) from the header. Each
property has its own corpus, its own citations and its own declared knowledge gaps.

It is model-agnostic: whatever ``VHOS_LLM_BACKEND`` is set to answers here unchanged.

    # open-weights model (e.g. Qwen on the Impala gateway) answering through the console
    VHOS_LLM_BACKEND=openweights VHOS_EMBED_BACKEND=local \
    VHOS_OPENWEIGHTS_URL=https://<gateway>/v1 VHOS_OPENWEIGHTS_MODEL=<model-id> \
    python ui/server.py

Standard library only.
"""
from __future__ import annotations

import json
import re
import sys
import threading
from datetime import date, datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from velocity_hos.agents.base import Context, RiskLevel  # noqa: E402
from velocity_hos.agents.executive_intelligence import ExecutiveIntelligenceAgent  # noqa: E402
from velocity_hos.agents.hr_onboarding import HROnboardingAgent  # noqa: E402
from velocity_hos.agents.sop_coach import SOPCoachAgent  # noqa: E402
from velocity_hos.agents.work_order import WorkOrderAgent  # noqa: E402
from velocity_hos.config import settings  # noqa: E402
from velocity_hos.knowledge import FINDINGS, get_property, property_index  # noqa: E402
from velocity_hos.orchestration.approval import ApprovalGate  # noqa: E402
from velocity_hos.orchestration.loop import ExecutionLoop  # noqa: E402

PORT = 8080
_LOCK = threading.Lock()

# Per-property demonstration state. Reset from the console at any time.
_STATE: dict[str, dict] = {}

_SLA_BY_ACTION = {"request_documents": 24, "escalate_permit": 48, "work_order": 4}
_OWNER_BY_AGENT = {
    "hr_onboarding": "HR / Owner-manager",
    "work_order": "Maintenance / Duty Manager",
    "sop_coach": "Department head",
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%H:%M:%SZ")


def _trail_row(e: dict, seq: int) -> dict:
    """One uniform trail row, whatever produced it (agent event or human decision)."""
    ts = str(e.get("ts", ""))
    if "T" in ts:                      # ISO timestamp from the audit trail
        ts = ts.split("T", 1)[1][:8] + "Z"
    return {"seq": seq, "ts": ts, "agent": e.get("agent", ""),
            "phase": e.get("phase", ""), "risk": e.get("risk", ""),
            "decision": e.get("decision", ""),
            "action": e.get("action") or e.get("action_type", ""),
            "sources": e.get("sources", []),
            "summary": _headline(e.get("summary", ""))[:150]}


_MD_MARKERS = re.compile(r"^[\s>*+-]*#{0,6}\s*|\*\*|__|`")


def _headline(text: str) -> str:
    """First line of a summary, with markdown markers stripped.

    Production models format freely — a capable model will hand back a briefing
    headed "**EXECUTIVE BRIEFING**" or bullets led with "*   ". That is correct model
    behaviour, but a single-line row in a table should read as prose, not as raw
    markdown. The full text is preserved untouched; only the row label is cleaned.
    """
    for line in (text or "").splitlines():
        cleaned = _MD_MARKERS.sub("", line).strip()
        if cleaned:
            return cleaned
    return ""


def _blank_state() -> dict:
    return {"cycle": None, "approvals": [], "tasks": [], "trail": [],
            "briefing": "", "ran_at": None, "answers": []}


def _state(pkey: str) -> dict:
    return _STATE.setdefault(get_property(pkey).key, _blank_state())


# --------------------------------------------------------------------------- info
def status(pkey: str | None) -> dict:
    prop = get_property(pkey)
    backend = settings.llm_backend
    model = {"bedrock": settings.bedrock_model_id,
             "openweights": settings.openweights_model}.get(
                 backend, "offline deterministic (proof)")
    return {
        "backend": backend, "model": model, "embed": settings.embed_backend,
        "property": {
            "key": prop.key, "name": prop.name, "subtitle": prop.subtitle,
            "location": prop.location, "kind": prop.kind, "provenance": prop.provenance,
            "sops": len(prop.sops), "departments": len(prop.departments()),
            "gaps": len(prop.gaps), "provenance_counts": prop.provenance_counts(),
            "samples": prop.sample_questions, "refusals": prop.refusal_questions,
        },
        "today": date.today().isoformat(),
    }


def api_kb(pkey: str) -> list[dict]:
    return [{"id": s.sop_id, "department": s.department, "title": s.title,
             "priority": s.priority, "confidence": s.confidence, "source": s.source,
             "summary": s.ai_summary}
            for s in get_property(pkey).sops]


def api_gaps(pkey: str) -> list[dict]:
    return [{"gid": g.get("gid"), "gap": g.get("gap"), "blocks": g.get("blocks"),
             "needed": g.get("needed_from_operator")} for g in get_property(pkey).gaps]


def api_evidence() -> list[dict]:
    return [f.__dict__ for f in FINDINGS]


# ---------------------------------------------------------------------------- ask
def ask(pkey: str, question: str) -> dict:
    prop = get_property(pkey)
    if not question:
        return {"ok": False, "error": "Type a question first.",
                "answer": "", "sources": [], "refused": False, "sop": None}
    ctx = Context(prop.tenant_id, {"question": question, "known_gaps": prop.gaps},
                  prop.retrieval_docs())
    rec = SOPCoachAgent().evaluate(ctx)[0]
    action = rec.proposed_action
    refused = action.get("type") == "refusal"
    by_id = {s.sop_id: s for s in prop.sops}
    sop = None
    if rec.sources and (s := by_id.get(rec.sources[0])):
        sop = {"id": s.sop_id, "title": s.title, "department": s.department,
               "ai_summary": s.ai_summary, "procedure": s.procedure,
               "decision_tree": [f"If {b.condition} → {b.action}" for b in s.decision_tree],
               "escalation": s.escalation_rules, "kpis": s.kpis,
               "related": s.related_sops, "confidence": s.confidence, "source": s.source}
    with _LOCK:
        _state(pkey)["answers"].append(
            {"q": question, "sop": rec.sources[:1], "refused": refused, "ts": _now()})
    return {"ok": True, "answer": rec.summary, "sources": rec.sources,
            "refused": refused, "gap_id": action.get("gap_id"),
            "gap": action.get("gap"), "sop": sop}


# --------------------------------------------------------------------------- loop
def _briefing_for(prop, activity: dict) -> str:
    ctx = Context(prop.tenant_id, {**prop.inputs(), "cycle_activity": activity},
                  prop.retrieval_docs())
    return ExecutiveIntelligenceAgent().evaluate(ctx)[0].summary


def _activity_from(st: dict) -> dict:
    """Rebuild the cycle summary from CURRENT state, so approving an item moves it out
    of 'awaiting' and into 'actions taken'. This is what makes the loop close."""
    return {
        "answered_for_staff": [a["summary"] for a in st["cycle"]["info"]],
        "actions_auto_executed": ([a["summary"] for a in st["cycle"]["auto"]]
                                  + [t["summary"] for t in st["tasks"]]),
        "awaiting_your_approval": [a["summary"] for a in st["approvals"]
                                   if a["decision"] == "pending"],
    }


def run_loop(pkey: str) -> dict:
    """Run one real cycle of the four-agent execution loop for this property."""
    prop = get_property(pkey)
    gate = ApprovalGate()
    agents = [SOPCoachAgent(), HROnboardingAgent(), WorkOrderAgent(),
              ExecutiveIntelligenceAgent()]
    result = ExecutionLoop(agents, gate).run(
        Context(prop.tenant_id, prop.inputs(), prop.retrieval_docs()))

    def row(rec) -> dict:
        return {"agent": rec.agent, "summary": _headline(rec.summary)[:170],
                "full": rec.summary, "risk": rec.risk.value,
                "action": rec.proposed_action.get("type", ""), "sources": rec.sources}

    approvals: list[dict] = []
    auto: list[dict] = []
    info: list[dict] = []
    for rec in result.recommendations:
        r = row(rec)
        if rec.risk is RiskLevel.REQUIRES_APPROVAL:
            approvals.append({**r, "id": len(approvals), "decision": "pending",
                              "decided_at": None})
        elif rec.risk is RiskLevel.LOW:
            auto.append(r)
        elif rec.proposed_action.get("type") == "answer":
            info.append(r)

    with _LOCK:
        st = _blank_state()
        st["cycle"] = {"all": [row(r) for r in result.recommendations],
                       "auto": auto, "info": info}
        st["approvals"] = approvals
        st["trail"] = [_trail_row(e, i + 1) for i, e in
                       enumerate(result.trail.to_list() if result.trail else [])]
        st["ran_at"] = _now()
        _STATE[prop.key] = st
        st["briefing"] = _briefing_for(prop, _activity_from(st))
    return _snapshot(pkey)


def decide(pkey: str, index: int, decision: str) -> dict:
    """Resolve one held item. Approval turns it into an assigned, SLA-bound task and
    regenerates the GM briefing, so the impact is visible in the same cycle."""
    prop = get_property(pkey)
    with _LOCK:
        st = _state(pkey)
        if not st["cycle"]:
            return {"ok": False, "error": "Run an operations cycle first."}
        if not (0 <= index < len(st["approvals"])):
            return {"ok": False, "error": "That approval item no longer exists."}
        item = st["approvals"][index]
        if item["decision"] != "pending":
            return {"ok": False, "error": "That item has already been decided."}
        if decision not in ("approved", "rejected"):
            return {"ok": False, "error": "Decision must be approved or rejected."}

        item["decision"] = decision
        item["decided_at"] = _now()
        st["trail"].append({
            "seq": len(st["trail"]) + 1, "ts": _now(), "agent": item["agent"],
            "phase": "human_decision", "risk": item["risk"], "decision": decision,
            "action": item["action"], "sources": item["sources"],
            "summary": item["summary"]})

        if decision == "approved":
            hours = _SLA_BY_ACTION.get(item["action"], 24)
            owner = _OWNER_BY_AGENT.get(item["agent"], "Duty Manager")
            st["tasks"].append({
                "summary": item["summary"], "agent": item["agent"],
                "action": item["action"], "sources": item["sources"], "owner": owner,
                "due": (datetime.now(timezone.utc) + timedelta(hours=hours))
                       .strftime("%Y-%m-%d %H:%M UTC"),
                "sla_hours": hours, "assigned_at": _now(), "status": "assigned"})
            st["trail"].append({
                "seq": len(st["trail"]) + 1, "ts": _now(), "agent": item["agent"],
                "phase": "execute", "risk": item["risk"], "decision": "executed",
                "action": item["action"], "sources": item["sources"],
                "summary": f"Assigned to {owner} · SLA {hours}h"})

        # The report phase runs again over the NEW state: the loop closing.
        st["briefing"] = _briefing_for(prop, _activity_from(st))
    snap = _snapshot(pkey)
    snap["ok"] = True
    return snap


def reset(pkey: str) -> dict:
    with _LOCK:
        _STATE[get_property(pkey).key] = _blank_state()
    return _snapshot(pkey)


def reset_all() -> dict:
    with _LOCK:
        _STATE.clear()
    return {"ok": True, "reset": "all"}


def _snapshot(pkey: str) -> dict:
    prop = get_property(pkey)
    st = _state(pkey)
    inputs = prop.inputs()
    pending = [a for a in st["approvals"] if a["decision"] == "pending"]
    decided = [a for a in st["approvals"] if a["decision"] != "pending"]
    return {
        "property": {"key": prop.key, "name": prop.name,
                     "subtitle": prop.subtitle, "kind": prop.kind},
        "ran": st["cycle"] is not None, "ran_at": st["ran_at"],
        # Copies, not references: a snapshot is a point-in-time view of the demo,
        # never a live handle onto server state.
        "recommendations": [dict(r) for r in (st["cycle"]["all"] if st["cycle"] else [])],
        "approvals": [dict(a) for a in st["approvals"]], "pending_count": len(pending),
        "decided_count": len(decided), "tasks": [dict(t) for t in st["tasks"]],
        "briefing": st["briefing"], "trail": [dict(e) for e in st["trail"]],
        "kpis": inputs.get("kpis", []), "open_items": inputs.get("open_items", []),
        "hires": [{"name": h["name"], "role": h.get("role", ""),
                   "start_date": h.get("start_date", ""),
                   "progress": h.get("onboarding_progress", 0),
                   "documents": h.get("documents", [])}
                  for h in inputs.get("new_hires", [])],
        "tickets": inputs.get("tickets", []), "answers": st["answers"],
    }


PAGE = r"""<!DOCTYPE html><html lang=en><head><meta charset=UTF-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Velocity Hospitality OS — Console</title>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&family=Inter:wght@400;500;600&display=swap" rel=stylesheet>
<style>
:root{--black:#0A0A0B;--charcoal:#17171A;--graphite:#1F1F24;--slate:#2A2A30;
--gold:#C9A24B;--gold-l:#E4C87D;
--grad:linear-gradient(135deg,#E4C87D,#C9A24B 45%,#A87B2E);--hair:rgba(201,162,75,.22);--glow:rgba(201,162,75,.14);
--white:#fff;--cream:#F5F1E8;--text:#ECEAE4;--muted:#9A968C;
--success:#34B36B;--warn:#E0A83B;--info:#6FA8DC;--danger:#D9544D;
--brand:'Poppins',system-ui,sans-serif;--body:'Inter',system-ui,sans-serif}
*{box-sizing:border-box}
body{margin:0;background:radial-gradient(1200px 600px at 80% -10%,#15130d,var(--black) 55%);color:var(--text);font-family:var(--body);-webkit-font-smoothing:antialiased}
a{color:var(--gold);text-decoration:none}
.logo{width:30px;height:26px;position:relative;display:inline-block;flex:0 0 auto}
.logo::before,.logo::after{content:"";position:absolute;top:0;width:10px;height:26px;background:var(--grad)}
.logo::before{left:3px;transform:skewX(20deg)}.logo::after{right:3px;transform:skewX(-20deg)}
.wm{font-family:var(--brand);font-weight:600;letter-spacing:.26em;color:var(--white);font-size:15px}
.sub{font-family:var(--brand);font-weight:600;font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:var(--cream)}
.label{font-family:var(--brand);font-size:10.5px;font-weight:600;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}
.muted{color:var(--muted)}.small{font-size:12px}.spacer{flex:1}
.top{display:flex;align-items:center;gap:13px;padding:12px 22px;border-bottom:1px solid var(--hair);background:rgba(16,16,18,.85);backdrop-filter:blur(6px);position:sticky;top:0;z-index:9;flex-wrap:wrap}
select{background:var(--graphite);color:var(--text);border:1px solid var(--hair);border-radius:999px;padding:7px 12px;font-family:var(--body);font-size:12.5px;outline:none;cursor:pointer}
select:focus{border-color:var(--gold)}
.layout{display:flex;min-height:calc(100vh - 54px)}
.nav{width:214px;flex:0 0 214px;border-right:1px solid var(--hair);padding:16px 10px;display:flex;flex-direction:column;gap:2px}
.nav a{display:flex;align-items:center;gap:10px;padding:9px 12px;border-radius:9px;color:var(--muted);font-size:13.5px;cursor:pointer;border:1px solid transparent}
.nav a:hover{color:var(--cream);background:rgba(201,162,75,.06)}
.nav a.active{color:var(--cream);background:var(--glow);border-color:var(--hair)}
.nav .ic{width:16px;text-align:center;color:var(--gold)}
.nav .cnt{margin-left:auto;font-size:10.5px;font-weight:700;color:#1A1206;background:var(--grad);border-radius:999px;padding:1px 7px}
.main{flex:1;padding:24px 26px 70px;max-width:1080px;min-width:0}
h1.title{font-family:var(--brand);font-weight:600;font-size:23px;margin:0 0 4px;color:var(--white)}
.crumb{font-size:13px;color:var(--muted);margin-bottom:16px;line-height:1.5}
.card{background:var(--charcoal);border:1px solid var(--hair);border-radius:14px;box-shadow:0 10px 30px rgba(0,0,0,.45);padding:18px;margin-bottom:14px}
.card h3{font-family:var(--brand);font-size:11.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--cream);margin:0 0 12px}
.grid{display:grid;gap:12px}
.k4{grid-template-columns:repeat(auto-fit,minmax(178px,1fr))}
.k2{grid-template-columns:repeat(auto-fit,minmax(318px,1fr))}
.tile .v{font-family:var(--brand);font-weight:600;font-size:31px;color:var(--white);line-height:1.15;margin-top:6px}
.tile .u{font-size:16px;color:var(--gold)}
.tile .d{font-size:11.5px;color:var(--muted);margin-top:2px}
.btn{font-family:var(--brand);font-weight:600;font-size:12px;letter-spacing:.04em;text-transform:uppercase;color:#1A1206;background:var(--grad);border:none;border-radius:999px;padding:10px 18px;cursor:pointer;box-shadow:0 8px 24px rgba(201,162,75,.16)}
.btn:hover{filter:brightness(1.07)}
.btn:disabled{opacity:.45;cursor:not-allowed;filter:none}
.btn.ghost{color:var(--gold);background:transparent;border:1px solid var(--gold);box-shadow:none}
.btn.ghost:hover{background:var(--glow)}
.btn.sm{padding:6px 13px;font-size:11px}
.pill{display:inline-flex;align-items:center;gap:5px;font-size:10.5px;font-weight:600;letter-spacing:.05em;text-transform:uppercase;padding:3px 9px;border-radius:999px;border:1px solid transparent;white-space:nowrap}
.pill.ok{color:var(--success);border-color:rgba(52,179,107,.4);background:rgba(52,179,107,.1)}
.pill.await{color:var(--warn);border-color:rgba(224,168,59,.4);background:rgba(224,168,59,.1)}
.pill.info{color:var(--info);border-color:rgba(111,168,220,.4);background:rgba(111,168,220,.1)}
.pill.risk{color:var(--danger);border-color:rgba(217,84,77,.4);background:rgba(217,84,77,.1)}
.pill.seed{color:var(--gold);border-color:var(--hair);background:var(--glow)}
.row{display:flex;gap:10px;align-items:center;padding:9px 0;border-bottom:1px solid rgba(201,162,75,.1);font-size:13.5px;flex-wrap:wrap}
.row:last-child{border-bottom:0}
.who{font-family:var(--brand);font-size:10px;letter-spacing:.05em;text-transform:uppercase;color:var(--gold);flex:0 0 118px}
input[type=text]{width:100%;background:var(--graphite);border:1px solid var(--hair);border-radius:999px;padding:12px 17px;color:var(--text);font-size:15px;font-family:var(--body);outline:none}
input[type=text]:focus{border-color:var(--gold);box-shadow:0 0 0 3px var(--glow)}
.ask{display:flex;gap:9px;align-items:center}
.chips{display:flex;flex-wrap:wrap;gap:7px;margin:12px 0 0}
.chip{font-size:12px;border:1px solid var(--hair);color:var(--muted);border-radius:999px;padding:6px 12px;cursor:pointer}
.chip:hover{color:var(--cream);border-color:var(--gold)}
.chip.refuse{border-style:dashed}
.answer{background:var(--graphite);border:1px solid var(--hair);border-radius:12px;padding:17px}
.answer.refuse{border-color:rgba(224,168,59,.45)}
.cite{font-family:var(--brand);font-weight:600;font-size:10.5px;letter-spacing:.07em;color:var(--gold);border:1px solid var(--hair);border-radius:999px;padding:3px 10px;display:inline-block}
.body{color:var(--cream);line-height:1.6;margin:11px 0 0;font-size:14px}
.kv{margin-top:11px;font-size:13px}
.kv .k{color:var(--muted);font-size:10.5px;letter-spacing:.06em;text-transform:uppercase;margin-top:11px}
.kv ul{margin:5px 0;padding-left:17px;line-height:1.55}
.note{font-size:12px;color:var(--muted);margin-top:11px;line-height:1.5;border-left:2px solid var(--hair);padding-left:10px}
.brief .mdh{display:block;color:var(--gold-l);font-family:var(--brand);font-size:11px;letter-spacing:.08em;text-transform:uppercase;margin:12px 0 4px}
.brief .mdli{display:block;padding-left:14px;text-indent:-9px}
.brief .mdli::before{content:'\2022 ';color:var(--gold)}
.brief{white-space:pre-wrap;line-height:1.6;color:var(--cream);font-size:13px;background:var(--graphite);border-radius:10px;padding:14px;border:1px solid var(--hair)}
.stage .h{display:flex;align-items:center;gap:10px;margin-bottom:10px}
.stage .n{width:22px;height:22px;border-radius:50%;background:var(--grad);color:#1A1206;font-family:var(--brand);font-weight:700;font-size:11.5px;display:flex;align-items:center;justify-content:center;flex:0 0 auto}
.stage b{font-family:var(--brand);font-size:12.5px;letter-spacing:.03em;color:var(--cream)}
table.trail{width:100%;border-collapse:collapse;font-size:11.5px;margin-top:4px;display:block;overflow-x:auto}
table.trail th{text-align:left;font-family:var(--brand);font-size:9.5px;letter-spacing:.09em;text-transform:uppercase;color:var(--muted);padding:6px 8px;border-bottom:1px solid var(--hair);white-space:nowrap}
table.trail td{padding:6px 8px;border-bottom:1px solid rgba(201,162,75,.08);color:var(--text);vertical-align:top}
table.trail code{color:var(--gold-l);font-size:11px}
.bar{height:5px;border-radius:99px;background:var(--slate);overflow:hidden;width:120px;flex:0 0 120px}
.hrow{flex-wrap:nowrap}.hrow .nm{flex:1 1 auto;min-width:0}.hrow .pc{flex:0 0 auto;white-space:nowrap}
.bar>i{display:block;height:100%;background:var(--grad)}
.err{border:1px solid rgba(217,84,77,.5);background:rgba(217,84,77,.08);color:#F0B4B0;border-radius:10px;padding:11px 14px;font-size:13px;margin-top:12px}
.okmsg{border:1px solid rgba(52,179,107,.4);background:rgba(52,179,107,.08);color:#A6E3C0;border-radius:10px;padding:11px 14px;font-size:13px;margin-top:12px}
.spin{display:inline-block;width:12px;height:12px;border:2px solid var(--hair);border-top-color:var(--gold);border-radius:50%;animation:sp .7s linear infinite;vertical-align:-1px;margin-right:7px}
@keyframes sp{to{transform:rotate(360deg)}}
.view{display:none}.view.on{display:block}
.banner{display:flex;gap:10px;align-items:flex-start;border:1px solid var(--hair);background:var(--glow);border-radius:11px;padding:11px 14px;font-size:12.5px;color:var(--cream);line-height:1.5;margin-bottom:15px;flex-wrap:wrap}
.gapcard{border-left:2px solid var(--warn);padding-left:12px;margin-bottom:13px}
@media(max-width:820px){
 .layout{flex-direction:column}
 .nav{width:auto;flex:none;flex-direction:row;overflow-x:auto;border-right:0;border-bottom:1px solid var(--hair);padding:8px}
 .nav a{white-space:nowrap;font-size:12.5px}
 .main{padding:18px 14px 60px}
 .who{flex:0 0 100%}
 h1.title{font-size:20px}
 .top{gap:9px;padding:10px 14px}
}
</style></head><body>
<div class=top>
  <span class=logo></span><span class=wm>VELOCITY</span><span class=sub>Hospitality OS</span>
  <span class=spacer></span>
  <span class=label style="letter-spacing:.1em">Property</span>
  <select id=psel onchange=switchProperty()></select>
  <span id=backend class="small muted"></span>
  <button class="btn ghost sm" onclick=resetDemo()>Reset demo</button>
</div>
<div class=layout>
  <nav class=nav id=nav>
    <a data-v=dash class=active><span class=ic>&#9703;</span> Dashboard</a>
    <a data-v=coach><span class=ic>&#9672;</span> SOP Coach</a>
    <a data-v=loop><span class=ic>&#9678;</span> Operations Loop</a>
    <a data-v=appr><span class=ic>&#9208;</span> Approvals <span class=cnt id=apprcnt style=display:none>0</span></a>
    <a data-v=kb><span class=ic>&#9636;</span> Knowledge Base</a>
    <a data-v=gaps><span class=ic>&#9676;</span> Knowledge Gaps</a>
    <a data-v=evi><span class=ic>&#9670;</span> Evidence</a>
  </nav>
  <main class=main>

    <section class="view on" id=v-dash>
      <h1 class=title>Operational Command</h1>
      <div class=crumb id=dashcrumb>Loading&hellip;</div>
      <div id=provbanner></div>
      <div class="grid k4" id=kpis></div>
      <div class="grid k2" style=margin-top:14px>
        <div class=card><h3>Awaiting your approval</h3><div id=dashappr></div>
          <div class=note>Consequential actions &mdash; contacting a hire, escalating a permit, dispatching safety work &mdash; never execute without a person. That control is the product.</div></div>
        <div class=card><h3>Today &middot; tasks &amp; alerts</h3><div id=dashalerts></div></div>
      </div>
      <div class="grid k2">
        <div class=card><h3>Onboarding in progress</h3><div id=dashhires></div></div>
        <div class=card><h3>Assigned after approval</h3><div id=dashtasks></div></div>
      </div>
      <div class=card><h3>GM daily briefing</h3><div id=dashbrief></div></div>
    </section>

    <section class=view id=v-coach>
      <h1 class=title>SOP Coach</h1>
      <div class=crumb>Ask anything. Answers are grounded strictly in this property's own records, with a citation &mdash; and it refuses, by name, when the property has no documented answer.</div>
      <div class=card>
        <div class=ask><input type=text id=q placeholder="ask a question&hellip;"><button class=btn onclick=ask()>Ask</button></div>
        <div class=chips id=chips></div>
      </div>
      <div id=ans></div>
    </section>

    <section class=view id=v-loop>
      <h1 class=title>Operations Loop</h1>
      <div class=crumb>Inputs &rarr; Agents &rarr; Human approval &rarr; Actions &rarr; Reporting. One coordinated cycle across four supervised agents, computed live by the Python product.</div>
      <div class=card>
        <button class=btn id=runbtn onclick=runLoop()>&#9654; Run one operations cycle</button>
        <button class="btn ghost" onclick=resetDemo()>Reset</button>
        <div class=note style=margin-top:12px>SOP Coach &middot; HR Onboarding &middot; Work Order &middot; Executive Intelligence. Nothing here is pre-recorded &mdash; every line is produced by the same agents the tests and the evaluation run against.</div>
      </div>
      <div id=loopout></div>
    </section>

    <section class=view id=v-appr>
      <h1 class=title>Human Approval</h1>
      <div class=crumb>Every held item, its governing source, and what happens the moment you decide. Approving assigns an owner and an SLA, writes the decision to the trail, and regenerates the GM briefing.</div>
      <div id=approut></div>
    </section>

    <section class=view id=v-kb>
      <h1 class=title>Knowledge Base</h1>
      <div class=crumb id=kbcrumb></div>
      <div id=kblist></div>
    </section>

    <section class=view id=v-gaps>
      <h1 class=title>Declared Knowledge Gaps</h1>
      <div class=crumb>Subjects this property has not yet documented. They are deliberately absent from the knowledge base, so the assistant refuses them <b>by name</b> and routes to a human &mdash; rather than answering from an adjacent record that merely shares vocabulary.</div>
      <div id=gaplist></div>
    </section>

    <section class=view id=v-evi>
      <h1 class=title>Evidence Base</h1>
      <div class=crumb>Every capability traces to a documented operational finding &mdash; from a direct on-site audit of a luxury resort plus cross-property operator interviews. Anonymised; no property named, no proprietary document reproduced.</div>
      <div id=evilist></div>
      <div class=note>Validation strength is preserved honestly: a pattern seen at &ge;2 independent properties (validated) is stronger than a single observation.</div>
    </section>

  </main>
</div>
<script>
let P = null, STATUS = null, SNAP = null;
const $ = function(id){ return document.getElementById(id); };
const esc = function(s){ return String(s==null?"":s).replace(/[&<>"]/g, function(c){ return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]; }); };
const li = function(a){ return (a||[]).map(function(x){ return "<li>"+esc(x)+"</li>"; }).join(""); };
// The briefing is written by whichever model is configured. Capable models format in
// markdown; the offline proof model returns plain text. Render both readably rather
// than showing a judge a screen of raw asterisks.
function mdlite(t){
  return esc(t||"")
    .replace(/^\s*#{1,6}\s*(.+)$/gm, '<b class=mdh>$1</b>')
    .replace(/\*\*(.+?)\*\*/g, '<b>$1</b>')
    .replace(/^\s*[*+-]\s+(.+)$/gm, '<span class=mdli>$1</span>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    // the container is pre-wrap, so a newline straight after a block element would
    // add a second, empty line — drop it and let the block do the spacing.
    .replace(/<\/span>\n/g, '</span>')
    .replace(/<\/b>\n/g, '</b>')
    .replace(/\n{3,}/g, '\n\n');
}
const qs = function(){ return "?p=" + encodeURIComponent(P); };

async function api(path, body){
  const opt = (body===undefined) ? {} : {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)};
  const r = await fetch(path, opt);
  if(!r.ok) throw new Error("server returned " + r.status);
  return r.json();
}
function fail(el, e){ $(el).innerHTML = '<div class=err><b>Something went wrong.</b><br>'+esc(e.message||e)+'<br><span class=small>The console keeps running &mdash; press the button again, or Reset demo.</span></div>'; }
function busy(el, msg){ $(el).innerHTML = '<div class="card small muted"><span class=spin></span>'+esc(msg)+'</div>'; }

async function boot(){
  const props = await api("/api/properties");
  P = new URLSearchParams(location.search).get("p") || props[0].key;
  $("psel").innerHTML = props.map(function(p){ return '<option value="'+esc(p.key)+'"'+(p.key===P?" selected":"")+'>'+esc(p.name)+" &middot; "+esc(p.subtitle)+"</option>"; }).join("");
  await loadProperty();
}
function switchProperty(){ P = $("psel").value; loadProperty(); }

async function loadProperty(){
  STATUS = await api("/api/status"+qs());
  const s = STATUS.property;
  $("backend").innerHTML = "backend <b>"+esc(STATUS.backend)+"</b> &middot; model <b>"+esc(STATUS.model)+"</b>";
  $("dashcrumb").innerHTML = esc(s.name)+" &middot; "+esc(s.location)+" &mdash; <b>"+s.sops+"</b> knowledge records across <b>"+s.departments+"</b> departments"+(s.gaps?", <b>"+s.gaps+"</b> declared gaps":"");
  $("provbanner").innerHTML = '<div class=banner><span class="pill seed">'+esc(s.kind)+'</span><span>'+esc(s.provenance)+'</span></div>';
  $("kbcrumb").innerHTML = "<b>"+s.sops+"</b> records across <b>"+s.departments+"</b> departments &mdash; RAG-ready. Swap in the property's own documents with no code change.";
  $("chips").innerHTML =
      s.samples.map(function(x){ return '<span class=chip onclick="ask(this.textContent)">'+esc(x)+'</span>'; }).join("")
    + s.refusals.map(function(x){ return '<span class="chip refuse" onclick="ask(this.textContent)">'+esc(x)+'</span>'; }).join("");
  $("ans").innerHTML = ""; $("q").value = "";
  await Promise.all([refresh(), loadKB(), loadGaps(), loadEvidence()]);
}

async function ask(text){
  const q = (typeof text === "string") ? text : $("q").value;
  if(!q || !q.trim()){ $("ans").innerHTML = '<div class=err>Type a question first.</div>'; return; }
  $("q").value = q;
  busy("ans","retrieving from this property's records…");
  try{
    const d = await api("/api/ask", {p:P, question:q});
    if(!d.ok){ $("ans").innerHTML = '<div class=err>'+esc(d.error)+'</div>'; return; }
    if(d.refused || !d.sop){
      const tag = d.gap_id ? ("Declared gap "+esc(d.gap_id)) : "No record found";
      const why = d.gap_id
        ? "This property has not documented this yet ("+esc(d.gap)+"). The assistant names the gap and routes to a human instead of answering from a neighbouring record."
        : "Grounding guardrail &mdash; the assistant refuses rather than invent policy.";
      $("ans").innerHTML = '<div class="card answer refuse"><span class="pill await">'+tag+' &middot; refused</span>'
        +'<p class=body>'+esc(d.answer)+'</p><div class=note>'+why+'</div></div>';
      return;
    }
    const s = d.sop;
    const prov = s.confidence === "operator_confirmed" ? '<span class="pill ok">Operator-confirmed</span>'
      : (s.confidence === "unconfirmed" ? '<span class="pill await">Unconfirmed &middot; public source: '+esc(s.source)+'</span>'
                                        : '<span class="pill info">Authored standard</span>');
    $("ans").innerHTML = '<div class="card answer"><span class=cite>&#9672; '+esc(s.id)+' &middot; '+esc(s.department)+'</span> '+prov
      +'<p class=body><b>'+esc(s.title)+'.</b> '+esc(s.ai_summary)+'</p>'
      +'<div class=kv><div class=k>Procedure</div><ul>'+li(s.procedure)+'</ul>'
      +(s.decision_tree.length?'<div class=k>Decisions</div><ul>'+li(s.decision_tree)+'</ul>':'')
      +(s.escalation.length?'<div class=k>Escalation</div><ul>'+li(s.escalation)+'</ul>':'')
      +(s.kpis.length?'<div class=k>KPIs</div><div>'+esc(s.kpis.join(" · "))+'</div>':'')
      +'</div><div class=note>Grounded and cited &middot; source '+esc(s.id)+(s.related.length?' &middot; related '+esc(s.related.join(", ")):'')+'</div></div>';
  }catch(e){ fail("ans", e); }
}

async function runLoop(){
  $("runbtn").disabled = true;
  busy("loopout","four agents reasoning over this property's day…");
  try{ SNAP = await api("/api/loop", {p:P}); renderAll(); go("loop"); }
  catch(e){ fail("loopout", e); }
  finally{ $("runbtn").disabled = false; }
}
async function decide(i, d){
  document.querySelectorAll(".decbtn").forEach(function(b){ b.disabled = true; });
  try{
    const r = await api("/api/decide", {p:P, index:i, decision:d});
    if(!r.ok){ fail("approut", new Error(r.error||"could not record that decision")); return; }
    SNAP = r; renderAll();
  }catch(e){ fail("approut", e); }
  finally{ document.querySelectorAll(".decbtn").forEach(function(b){ b.disabled = false; }); }
}
async function resetDemo(){
  try{ SNAP = await api("/api/reset", {p:P}); $("ans").innerHTML=""; $("q").value=""; renderAll(); }
  catch(e){ fail("loopout", e); }
}
async function refresh(){ SNAP = await api("/api/state"+qs()); renderAll(); }

function riskPill(r){
  return r==="requires_approval" ? '<span class="pill await">&#9208; Held for human</span>'
       : r==="low" ? '<span class="pill ok">&#10003; Auto &middot; logged</span>'
       : '<span class="pill info">&#8505; Info</span>';
}
function renderAll(){ renderDash(); renderLoop(); renderAppr(); }

function renderDash(){
  const d = SNAP;
  $("kpis").innerHTML = (d.kpis||[]).map(function(k){
    return '<div class="card tile"><span class=label>'+esc(k.label)+'</span><div class=v>'
      +(k.unit==="€"?'<span class=u>€</span>':"")+esc(k.value)
      +(k.unit&&k.unit!=="€"?'<span class=u>'+esc(k.unit)+'</span>':"")
      +'</div><div class=d>'+esc(k.delta)+'</div></div>'; }).join("");
  $("dashalerts").innerHTML = (d.open_items||[]).map(function(a){
    return '<div class=row><span class="pill '+esc(a.kind)+'">'+esc(a.label)+'</span> '+esc(a.text)+'</div>'; }).join("");
  const pend = (d.approvals||[]).filter(function(a){ return a.decision==="pending"; });
  $("dashappr").innerHTML = !d.ran
    ? '<div class="row muted small">Run one operations cycle to populate live items &rarr;</div>'
    : (pend.length ? pend.map(function(a){ return '<div class=row><span class="pill await">Awaiting</span> '+esc(a.summary)+'</div>'; }).join("")
                   : '<div class=row><span class="pill ok">Clear</span> Every held item has been decided.</div>');
  $("dashhires").innerHTML = (d.hires||[]).map(function(h){
    return '<div class="row hrow"><span class=nm>'+esc(h.name)+' <span class="muted small">&middot; '+esc(h.role||"role TBD")+' &middot; starts '+esc(h.start_date)+'</span></span>'
      +'<span class=bar><i style="width:'+(h.progress||0)+'%"></i></span><span class="small muted pc">'+(h.progress||0)+'%</span></div>'; }).join("")
    || '<div class="row muted small">No hires in the pipeline.</div>';
  $("dashtasks").innerHTML = (d.tasks||[]).length
    ? d.tasks.map(function(t){ return '<div class=row><span class="pill ok">Assigned</span> '+esc(t.summary)+'<span class=spacer></span><span class="small muted">'+esc(t.owner)+' &middot; due '+esc(t.due)+'</span></div>'; }).join("")
    : '<div class="row muted small">Nothing assigned yet &mdash; approve a held item and it lands here with an owner and an SLA.</div>';
  $("dashbrief").innerHTML = d.briefing
    ? '<div class=brief>'+mdlite(d.briefing)+'</div><div class=note>Regenerated by the Executive Intelligence agent every time you decide &mdash; approved items move out of &ldquo;awaiting&rdquo; and into &ldquo;actions taken&rdquo;. That is the loop closing.</div>'
    : '<div class="row muted small">Run one operations cycle to generate today\'s briefing.</div>';
  const c = $("apprcnt");
  if(pend.length){ c.style.display=""; c.textContent = pend.length; } else { c.style.display="none"; }
}

function renderLoop(){
  const d = SNAP;
  if(!d.ran){ $("loopout").innerHTML = '<div class="card muted small">No cycle has been run yet for '+esc(d.property.name)+'.</div>'; return; }
  const rows = (d.recommendations||[]).map(function(r){
    return '<div class=row><span class=who>'+esc(r.agent)+'</span><span>'+esc(r.summary)
      +(r.sources.length?' <span class="muted small">[source '+esc(r.sources.join(", "))+']</span>':"")
      +'</span><span class=spacer></span>'+riskPill(r.risk)+'</div>'; }).join("");
  const pend = (d.approvals||[]).filter(function(a){ return a.decision==="pending"; });
  const gate = (d.approvals||[]).length
    ? d.approvals.map(function(a){
        return '<div class=row><span class=who>approval</span><span>'+esc(a.summary)
          +(a.sources.length?' <span class="muted small">[source '+esc(a.sources.join(", "))+']</span>':"")+'</span><span class=spacer></span>'
          + (a.decision==="pending"
              ? '<button class="btn sm decbtn" onclick="decide('+a.id+',\'approved\')">Approve</button> <button class="btn ghost sm decbtn" onclick="decide('+a.id+',\'rejected\')">Reject</button>'
              : (a.decision==="approved" ? '<span class="pill ok">&#10003; Approved &rarr; assigned &amp; logged</span>'
                                         : '<span class="pill risk">&#10007; Rejected &rarr; logged, no action</span>'))
          +'</div>'; }).join("")
    : '<div class="row muted small">No consequential actions this cycle.</div>';
  const trail = '<table class=trail><tr><th>#</th><th>Time</th><th>Agent</th><th>Phase</th><th>Risk</th><th>Decision</th><th>Action</th><th>Sources</th></tr>'
    + (d.trail||[]).map(function(e){
        return '<tr><td>'+esc(e.seq)+'</td><td>'+esc(e.ts||"")+'</td><td>'+esc(e.agent)+'</td><td>'+esc(e.phase)+'</td><td>'+esc(e.risk)+'</td><td>'+esc(e.decision)+'</td><td><code>'+esc(e.action)+'</code></td><td>'+esc((e.sources||[]).join(", ")||"—")+'</td></tr>'; }).join("")
    + '</table>';
  $("loopout").innerHTML =
    '<div class="card stage"><div class=h><span class=n>1</span><b>Inputs &mdash; one property, one day of operational exhaust</b></div><div class="small muted">'
      +(d.hires||[]).length+' new hires in the pipeline &middot; '+(d.tickets||[]).length+' maintenance / guest-request tickets &middot; '+(d.open_items||[]).length+' operational alerts &middot; 1 staff question</div></div>'
   +'<div class="card stage"><div class=h><span class=n>2</span><b>Agents reason against the property\'s own standards</b></div>'+rows+'</div>'
   +'<div class="card stage"><div class=h><span class=n>3</span><b>Human approval &mdash; nothing consequential acts without a person</b></div>'+gate
      +'<div class=note>'+pend.length+' item(s) still awaiting a decision. Approve one and watch stages 4 and 5 change.</div></div>'
   +'<div class="card stage"><div class=h><span class=n>4</span><b>Actions &mdash; approved items become owned, SLA-bound tasks</b></div>'
      +((d.tasks||[]).length ? d.tasks.map(function(t){ return '<div class=row><span class="pill ok">'+esc(t.action)+'</span> '+esc(t.summary)+'<span class=spacer></span><span class="small muted">'+esc(t.owner)+' &middot; SLA '+esc(t.sla_hours)+'h &middot; due '+esc(t.due)+'</span></div>'; }).join("")
                            : '<div class="row muted small">Nothing assigned yet.</div>')+'</div>'
   +'<div class="card stage"><div class=h><span class=n>5</span><b>Reporting &mdash; the GM briefing, regenerated after every decision</b></div><div class=brief>'+esc(d.briefing)+'</div></div>'
   +'<div class="card stage"><div class=h><span class=n>6</span><b>Decision trail &mdash; inspectable end to end</b></div>'+trail+'</div>';
}

function renderAppr(){
  const d = SNAP;
  if(!d.ran){ $("approut").innerHTML = '<div class="card muted small">Run one operations cycle to generate items for approval.</div>'; return; }
  if(!(d.approvals||[]).length){ $("approut").innerHTML = '<div class="card muted small">This cycle produced nothing that needs a human decision.</div>'; return; }
  const owners = {hr_onboarding:"HR / Owner-manager", work_order:"Maintenance / Duty Manager"};
  $("approut").innerHTML = d.approvals.map(function(a){
    return '<div class=card><div class=row style=border:0><span class=who>'+esc(a.agent)+'</span><b>'+esc(a.summary)+'</b><span class=spacer></span>'
      + (a.decision==="pending" ? '<span class="pill await">Awaiting you</span>'
         : a.decision==="approved" ? '<span class="pill ok">Approved '+esc(a.decided_at||"")+'</span>'
         : '<span class="pill risk">Rejected '+esc(a.decided_at||"")+'</span>')+'</div>'
      +'<div class=kv><div class=k>Proposed action</div><div><code style="color:var(--gold-l)">'+esc(a.action)+'</code></div>'
      +'<div class=k>Governing source</div><div>'+esc((a.sources||[]).join(", ")||"— no governing record; flagged so a human can close the gap")+'</div>'
      +'<div class=k>If approved</div><div>Assigned to '+esc(owners[a.agent]||"Duty Manager")+', written to the decision trail, and folded into the GM briefing.</div></div>'
      + (a.decision==="pending"
          ? '<div style=margin-top:13px><button class="btn decbtn" onclick="decide('+a.id+',\'approved\')">Approve</button> <button class="btn ghost decbtn" onclick="decide('+a.id+',\'rejected\')">Reject</button></div>'
          : '<div class=okmsg>Decision recorded at '+esc(a.decided_at||"")+' and written to the audit trail.</div>')
      +'</div>'; }).join("");
}

async function loadKB(){
  try{
    const kb = await api("/api/kb"+qs());
    const depts = [];
    kb.forEach(function(s){ if(depts.indexOf(s.department)<0) depts.push(s.department); });
    $("kblist").innerHTML = depts.map(function(dep){
      const items = kb.filter(function(s){ return s.department===dep; });
      return '<div class=card><h3>'+esc(dep)+' <span class="muted small" style="text-transform:none;letter-spacing:0">&middot; '+items.length+'</span></h3>'
        + items.map(function(s){
            const prov = s.confidence==="unconfirmed" ? '<span class="pill await">unconfirmed</span>'
                       : s.confidence==="operator_confirmed" ? '<span class="pill ok">confirmed</span>' : "";
            return '<div class=row><span class=cite>'+esc(s.id)+'</span> <b>'+esc(s.title)+'</b><span class=spacer></span>'+prov
              +' <span class="pill '+(s.priority==="critical"?"risk":(s.priority==="high"?"await":"info"))+'">'+esc(s.priority)+'</span></div>';
          }).join("") + '</div>';
    }).join("");
  }catch(e){ fail("kblist", e); }
}

async function loadGaps(){
  try{
    const g = await api("/api/gaps"+qs());
    $("gaplist").innerHTML = g.length
      ? '<div class=card>'+g.map(function(x){
          return '<div class=gapcard><div><span class=cite>'+esc(x.gid)+'</span> <b>'+esc(x.gap)+'</b></div>'
            +'<div class="small muted" style=margin-top:5px>'+esc(x.blocks)+'</div>'
            +'<div class=small style=margin-top:4px><span class=label>Needed from the operator</span> &middot; '+esc(x.needed)+'</div></div>'; }).join("")+'</div>'
      : '<div class="card muted small">This property has no declared gaps &mdash; its corpus is authored and complete.</div>';
  }catch(e){ fail("gaplist", e); }
}

async function loadEvidence(){
  try{
    const ev = await api("/api/evidence");
    const vmap = {validated:["ok","Validated · ≥2 sources"],reported:["await","Reported · 1 source"],"single-observation":["risk","Single observation"]};
    $("evilist").innerHTML = ev.map(function(f){
      const v = vmap[f.validation] || ["info", f.validation];
      return '<div class=card><div class=row style=border:0><span class=cite>'+esc(f.fid)+'</span> <b>'+esc(f.theme)+'</b><span class=spacer></span>'
        +'<span class="pill '+v[0]+'">'+esc(v[1])+'</span> '+(f.status==="live"?'<span class="pill ok">Live</span>':'<span class="pill info">Roadmap</span>')+'</div>'
        +'<p class=body style="margin:6px 0 0">'+esc(f.observation)+'</p>'
        +'<div class=kv><div class=k>Business impact</div><div>'+esc(f.business_impact)+'</div>'
        +'<div class=k>Addressed by</div><div style=color:var(--gold)>'+esc((f.addressed_by||[]).join(" · "))+'</div>'
        +'<div class=k>Source</div><div class="muted small">'+esc(f.sources)+'</div></div></div>'; }).join("");
  }catch(e){ fail("evilist", e); }
}

function go(v){
  document.querySelectorAll("#nav a").forEach(function(a){ a.classList.toggle("active", a.dataset.v===v); });
  document.querySelectorAll(".view").forEach(function(s){ s.classList.toggle("on", s.id==="v-"+v); });
  window.scrollTo({top:0,behavior:"smooth"});
}
document.querySelectorAll("#nav a").forEach(function(a){ a.onclick = function(){ go(a.dataset.v); }; });
$("q").addEventListener("keydown", function(e){ if(e.key==="Enter") ask(); });
boot().catch(function(e){ document.querySelector(".main").innerHTML = '<div class=err><b>The console could not start.</b><br>'+esc(e.message)+'</div>'; });
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _param(self, name: str, default: str = "") -> str:
        return (parse_qs(urlparse(self.path).query).get(name) or [default])[0]

    def do_GET(self):  # noqa: N802
        route = self.path.split("?")[0]
        try:
            if route in ("/", "/index", "/index.html"):
                return self._send(200, PAGE, "text/html; charset=utf-8")
            if route == "/api/properties":
                return self._send(200, json.dumps(property_index()))
            if route == "/api/status":
                return self._send(200, json.dumps(status(self._param("p"))))
            if route == "/api/state":
                return self._send(200, json.dumps(_snapshot(self._param("p"))))
            if route == "/api/kb":
                return self._send(200, json.dumps(api_kb(self._param("p"))))
            if route == "/api/gaps":
                return self._send(200, json.dumps(api_gaps(self._param("p"))))
            if route == "/api/evidence":
                return self._send(200, json.dumps(api_evidence()))
            if route == "/healthz":
                return self._send(200, json.dumps({"ok": True}))
            return self._send(404, json.dumps({"error": "not found"}))
        except Exception as exc:  # never let the console die mid-demonstration
            return self._send(500, json.dumps({"ok": False, "error": str(exc)}))

    def do_POST(self):  # noqa: N802
        route = self.path.split("?")[0]
        length = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw or b"{}")
            if not isinstance(body, dict):
                body = {}
        except json.JSONDecodeError:
            return self._send(400, json.dumps({"ok": False, "error": "Malformed JSON body."}))
        pkey = body.get("p") or self._param("p")
        try:
            if route == "/api/ask":
                return self._send(200, json.dumps(ask(pkey, (body.get("question") or "").strip())))
            if route == "/api/loop":
                return self._send(200, json.dumps(run_loop(pkey)))
            if route == "/api/decide":
                try:
                    idx = int(body.get("index"))
                except (TypeError, ValueError):
                    return self._send(400, json.dumps(
                        {"ok": False, "error": "index must be a number."}))
                return self._send(200, json.dumps(decide(pkey, idx, body.get("decision", ""))))
            if route == "/api/reset":
                return self._send(200, json.dumps(reset(pkey)))
            if route == "/api/reset-all":
                return self._send(200, json.dumps(reset_all()))
            return self._send(404, json.dumps({"error": "not found"}))
        except Exception as exc:
            return self._send(500, json.dumps({"ok": False, "error": str(exc)}))

    def log_message(self, *args):  # quiet
        pass


def main() -> int:
    info = status(None)
    print(f"Velocity Hospitality OS console → http://localhost:{PORT}")
    print(f"  backend: {info['backend']}   model: {info['model']}")
    for p in property_index():
        print(f"  property: {p['name']:<24} {p['sops']:>3} records · "
              f"{p['departments']:>2} departments · {p['gaps']} declared gaps")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
