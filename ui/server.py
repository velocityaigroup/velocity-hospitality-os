"""Velocity Hospitality OS — live web console (dependency-free).

    python ui/server.py         # then open http://localhost:8080

A branded, single-file web console served by the SAME Python agents, hybrid
retrieval, grounding guardrail, and human-approval loop used everywhere else —
served live, not mocked. Every SOP Coach answer and every operations cycle here is
computed server-side by the real product over the full demo knowledge base. It is
model-agnostic: whatever ``VHOS_LLM_BACKEND`` is set to (offline proof model, or an
open-weights model on the H200) answers here unchanged. Standard library only.

    # open-weights model (e.g. on the provided H200) answering through the console:
    VHOS_LLM_BACKEND=openweights VHOS_EMBED_BACKEND=local \
    VHOS_OPENWEIGHTS_URL=http://<gpu-host>:8000/v1 VHOS_OPENWEIGHTS_MODEL=<hf-id> \
    python ui/server.py
"""
from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from velocity_hos.agents.base import Context  # noqa: E402
from velocity_hos.agents.executive_intelligence import ExecutiveIntelligenceAgent  # noqa: E402
from velocity_hos.agents.hr_onboarding import HROnboardingAgent  # noqa: E402
from velocity_hos.agents.sop_coach import SOPCoachAgent  # noqa: E402
from velocity_hos.config import settings  # noqa: E402
from velocity_hos.knowledge import DEMO_SOPS, FINDINGS, demo_retrieval_docs, departments  # noqa: E402
from velocity_hos.orchestration.approval import ApprovalDecision, ApprovalGate  # noqa: E402
from velocity_hos.orchestration.loop import ExecutionLoop  # noqa: E402

PORT = 8080
KB_DOCS = demo_retrieval_docs()
SOP_BY_ID = {s.sop_id: s for s in DEMO_SOPS}


def backend_label() -> dict:
    b = settings.llm_backend
    model = {"bedrock": settings.bedrock_model_id,
             "openweights": settings.openweights_model}.get(b, "offline deterministic (proof)")
    return {"backend": b, "model": model, "embed": settings.embed_backend,
            "sops": len(DEMO_SOPS), "departments": len(departments())}


def ask(question: str) -> dict:
    if not question:
        return {"answer": "(no question)", "sources": [], "refused": False, "sop": None}
    rec = SOPCoachAgent().evaluate(Context("ui", {"question": question}, KB_DOCS))[0]
    refused = rec.proposed_action.get("type") == "refusal"
    sop = None
    if rec.sources and (s := SOP_BY_ID.get(rec.sources[0])):
        sop = {"id": s.sop_id, "title": s.title, "department": s.department,
               "ai_summary": s.ai_summary, "procedure": s.procedure,
               "decision_tree": [f"If {b.condition} → {b.action}" for b in s.decision_tree],
               "escalation": s.escalation_rules, "kpis": s.kpis,
               "related": s.related_sops}
    return {"answer": rec.summary, "sources": rec.sources, "refused": refused, "sop": sop}


def run_loop() -> dict:
    inputs = {
        "question": "how much rum goes in a mojito?",
        "new_hires": [
            {"id": "H-101", "name": "Ana P.", "role": "f&b",
             "documents": ["passport", "contract", "tax_form"],
             "permit_expiry": "2026-08-20", "start_date": "2026-08-10"},
            {"id": "H-102", "name": "Marko D.", "role": "front office",
             "documents": ["passport", "work_permit", "contract", "tax_form"],
             "start_date": "2026-08-12"},
        ],
        "signals": {"risks": ["Storm warning Thursday PM — pool & watersports"],
                    "staffing_alerts": ["F&B short 2 covers for Friday peak"],
                    "revenue_alerts": ["Cabanas unbooked this weekend"],
                    "compliance_alerts": ["1 work permit expiring within 30 days"]},
    }
    gate = ApprovalGate()
    result = ExecutionLoop([SOPCoachAgent(), HROnboardingAgent(),
                            ExecutiveIntelligenceAgent()], gate).run(
        Context("azure-bay-demo", inputs, KB_DOCS))
    pending = [p.recommendation.summary for p in gate.queue]
    briefing = next((r.summary for r in result.recommendations
                     if r.agent == "executive_intelligence"), "")
    return {
        "recommendations": [
            {"agent": r.agent, "summary": r.summary.splitlines()[0][:130],
             "risk": r.risk.value, "sources": r.sources}
            for r in result.recommendations],
        "held_for_human": pending,
        "briefing": briefing,
        "trail": result.trail.to_list() if result.trail else [],
        "audit_events": len(result.audit),
    }


def api_kb() -> list:
    return [{"id": s.sop_id, "department": s.department, "title": s.title,
             "priority": s.priority} for s in DEMO_SOPS]


def api_evidence() -> list:
    return [f.__dict__ for f in FINDINGS]


PAGE = r"""<!DOCTYPE html><html lang=en><head><meta charset=UTF-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Velocity Hospitality OS</title>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&family=Inter:wght@400;500;600&display=swap" rel=stylesheet>
<style>
:root{--black:#0A0A0B;--charcoal:#17171A;--graphite:#1F1F24;--gold:#C9A24B;--gold-l:#E4C87D;--gold-d:#A87B2E;
--grad:linear-gradient(135deg,#E4C87D,#C9A24B 45%,#A87B2E);--hair:rgba(201,162,75,.22);--glow:rgba(201,162,75,.14);
--white:#fff;--cream:#F5F1E8;--text:#ECEAE4;--muted:#9A968C;--success:#34B36B;--warn:#E0A83B;--info:#6FA8DC;--danger:#D9544D;
--brand:'Poppins',sans-serif;--body:'Inter',system-ui,sans-serif}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(1000px 500px at 80% -10%,#15130d,var(--black) 55%);color:var(--text);font-family:var(--body)}
.wrap{max-width:900px;margin:0 auto;padding:26px 22px 60px}
.top{display:flex;align-items:center;gap:14px;margin-bottom:6px}
.logo{width:28px;height:24px;position:relative;flex:0 0 auto}
.logo::before,.logo::after{content:"";position:absolute;top:0;width:9px;height:24px;background:var(--grad)}
.logo::before{left:3px;transform:skewX(20deg)}.logo::after{right:3px;transform:skewX(-20deg)}
.wm{font-family:var(--brand);font-weight:600;letter-spacing:.24em;color:var(--white)}.wm .a{color:var(--gold)}
.sub{font-family:var(--brand);font-weight:600;font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:var(--cream)}
.badge{display:inline-flex;gap:8px;align-items:center;border:1px solid var(--hair);border-radius:999px;padding:5px 12px;font-size:12px;color:var(--cream);margin:8px 0 18px}
.dot{width:7px;height:7px;border-radius:50%;background:var(--success);box-shadow:0 0 8px var(--success)}
.card{background:var(--charcoal);border:1px solid var(--hair);border-radius:14px;padding:20px;margin:16px 0;box-shadow:0 10px 30px rgba(0,0,0,.45)}
h2{font-family:var(--brand);font-size:12px;letter-spacing:.09em;text-transform:uppercase;color:var(--cream);margin:0 0 12px}
input{width:100%;background:var(--graphite);border:1px solid var(--hair);border-radius:999px;padding:12px 16px;color:var(--text);font-size:15px;font-family:var(--body);outline:none}
input:focus{border-color:var(--gold);box-shadow:0 0 0 3px var(--glow)}
button{font-family:var(--brand);font-weight:600;font-size:12.5px;letter-spacing:.04em;text-transform:uppercase;color:#1A1206;background:var(--grad);border:0;border-radius:999px;padding:11px 20px;cursor:pointer;margin-top:12px}
button.ghost{background:transparent;color:var(--gold);border:1px solid var(--gold)}
.chips{display:flex;flex-wrap:wrap;gap:7px;margin:12px 0}
.chip{font-size:12px;border:1px solid var(--hair);color:var(--muted);border-radius:999px;padding:6px 12px;cursor:pointer}.chip:hover{color:var(--cream);border-color:var(--gold)}
.answer{background:var(--graphite);border:1px solid var(--hair);border-radius:12px;padding:16px;margin-top:12px}
.answer.refuse{border-color:rgba(224,168,59,.4)}
.cite{font-family:var(--brand);font-weight:600;font-size:11px;letter-spacing:.07em;color:var(--gold);border:1px solid var(--hair);border-radius:999px;padding:3px 10px}
.answer .b{color:var(--cream);line-height:1.55;margin:10px 0 0}
.kv{margin-top:10px;font-size:13px}.kv .k{color:var(--muted);font-size:11px;letter-spacing:.05em;text-transform:uppercase;margin-top:8px}.kv ul{margin:4px 0;padding-left:16px}
.row{display:flex;gap:9px;align-items:baseline;padding:7px 0;border-bottom:1px solid rgba(201,162,75,.1);font-size:13.5px}
.who{font-family:var(--brand);font-size:10px;letter-spacing:.05em;text-transform:uppercase;color:var(--gold);flex:0 0 130px}
.tag{font-size:10px;font-weight:700;text-transform:uppercase;padding:2px 8px;border-radius:6px;white-space:nowrap}
.tag.hold{background:rgba(224,168,59,.12);color:var(--warn)}.tag.info{background:rgba(111,168,220,.12);color:var(--info)}.tag.low{background:rgba(52,179,107,.12);color:var(--success)}
.brief{white-space:pre-wrap;line-height:1.55;color:var(--cream);font-size:13px;margin-top:8px}
.mini{font-size:12px;color:var(--muted)}.spacer{flex:1}
</style></head><body><div class=wrap>
<div class=top><span class=logo></span><span class=wm>VELOCITY</span><span class=sub>Hospitality OS</span></div>
<div class=badge id=badge><span class=dot></span> loading…</div>

<div class=card>
  <h2>SOP Coach — grounded &amp; cited over the knowledge base</h2>
  <input id=q placeholder="e.g. how much rum goes in a mojito?  ·  a guest collapsed, what do we do?">
  <div class=chips id=chips></div>
  <button onclick=ask()>Ask</button>
  <div id=ans></div>
</div>

<div class=card>
  <h2>Operations Loop — Inputs → Agents → Human approval → Reporting</h2>
  <p class=mini>One live cycle across three supervised agents on a property's day of inputs. Consequential actions are held for a human; the GM briefing reflects what the cycle did.</p>
  <button class=ghost onclick=loop()>Run one operations cycle</button>
  <div id=loop></div>
</div>
<div class=mini>Model-agnostic &amp; self-hosted — the active model is shown above; swap it (offline proof ↔ open-weights on H200) with zero code change.</div>
</div><script>
const EX=["how much rum goes in a mojito?","which documents does a new kitchen hire need?","a guest collapsed, what do we do?","the power went out, what's the procedure?","what is the capital of France?"];
const chips=document.getElementById('chips');EX.forEach(e=>{const c=document.createElement('span');c.className='chip';c.textContent=e;c.onclick=()=>{q.value=e;ask()};chips.appendChild(c)});
fetch('/api/status').then(r=>r.json()).then(s=>{badge.innerHTML='<span class=dot></span> backend <b>'+s.backend+'</b> · model <b>'+s.model+'</b> · <b>'+s.sops+'</b> SOPs / '+s.departments+' departments'});
function li(a){return (a||[]).map(x=>'<li>'+x+'</li>').join('')}
function ask(){const a=document.getElementById('ans');a.innerHTML='<div class=mini>thinking…</div>';
 fetch('/api/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:q.value})}).then(r=>r.json()).then(d=>{
 if(d.refused||!d.sop){a.innerHTML='<div class="answer refuse"><span class=cite>No SOP · refused</span><p class=b>'+d.answer+'</p><div class=mini>Grounding guardrail — refuses rather than invent policy.</div></div>';return}
 const s=d.sop;
 a.innerHTML='<div class=answer><span class=cite>◈ '+s.id+' · '+s.department+'</span><p class=b><b>'+s.title+'.</b> '+s.ai_summary+'</p>'
 +'<div class=kv><div class=k>Procedure</div><ul>'+li(s.procedure)+'</ul>'
 +(s.decision_tree.length?'<div class=k>Decisions</div><ul>'+li(s.decision_tree)+'</ul>':'')
 +(s.escalation.length?'<div class=k>Escalation</div><ul>'+li(s.escalation)+'</ul>':'')
 +(s.kpis.length?'<div class=k>KPIs</div><div>'+s.kpis.join(' · ')+'</div>':'')
 +'</div><div class=mini style=margin-top:8px>Grounded &amp; cited · source '+s.id+' · related '+(s.related.join(', ')||'—')+'</div></div>'})}
function loop(){const L=document.getElementById('loop');L.innerHTML='<div class=mini>running…</div>';
 fetch('/api/loop',{method:'POST'}).then(r=>r.json()).then(d=>{
 let recs=d.recommendations.map(r=>{let t=r.risk=='requires_approval'?'<span class="tag hold">held for human</span>':(r.risk=='low'?'<span class="tag low">auto</span>':'<span class="tag info">info</span>');
   let src=r.sources.length?' <span class=mini>['+r.sources.join(', ')+']</span>':'';
   return '<div class=row><span class=who>'+r.agent+'</span><span>'+r.summary+src+'</span><span class=spacer></span>'+t+'</div>'}).join('');
 L.innerHTML='<div style=margin-top:10px>'+recs+'</div>'
  +'<div class=kv><div class=k>GM daily briefing (reflects this cycle)</div><div class=brief>'+d.briefing+'</div></div>'
  +'<div class=mini style=margin-top:10px><b>'+d.held_for_human.length+'</b> item(s) awaiting your approval · <b>'+d.audit_events+'</b> events in the decision trail</div>'})}
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):  # noqa: N802
        if self.path == "/" or self.path.startswith("/index"):
            return self._send(200, PAGE, "text/html; charset=utf-8")
        if self.path == "/api/status":
            return self._send(200, json.dumps(backend_label()))
        if self.path == "/api/kb":
            return self._send(200, json.dumps(api_kb()))
        if self.path == "/api/evidence":
            return self._send(200, json.dumps(api_evidence()))
        return self._send(404, json.dumps({"error": "not found"}))

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            body = {}
        if self.path == "/api/ask":
            return self._send(200, json.dumps(ask((body.get("question") or "").strip())))
        if self.path == "/api/loop":
            return self._send(200, json.dumps(run_loop()))
        return self._send(404, json.dumps({"error": "not found"}))

    def log_message(self, *args):  # quiet
        pass


def main() -> int:
    info = backend_label()
    print(f"Velocity Hospitality OS console → http://localhost:{PORT}")
    print(f"  backend: {info['backend']}   model: {info['model']}")
    print(f"  knowledge base: {info['sops']} SOPs across {info['departments']} departments")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
