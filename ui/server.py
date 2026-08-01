"""Velocity Hospitality OS — local web UI (dependency-free).

    python ui/server.py         # then open http://localhost:8080

A single-file web UI over the SAME agents, retrieval, guardrail and human-approval
loop used everywhere else — it just renders them. It is model-agnostic: whatever
VHOS_LLM_BACKEND is set to (local proof model, or an open-weights model on the
H200) answers here, unchanged. Uses only the Python standard library.

    # local proof model via Ollama:
    VHOS_LLM_BACKEND=openweights VHOS_EMBED_BACKEND=local \
    VHOS_OPENWEIGHTS_URL=http://localhost:11434/v1 VHOS_OPENWEIGHTS_MODEL=qwen3 \
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
from velocity_hos.data import SEED_SOPS  # noqa: E402
from velocity_hos.orchestration.approval import ApprovalDecision, ApprovalGate  # noqa: E402
from velocity_hos.orchestration.loop import ExecutionLoop  # noqa: E402

PORT = 8080


def backend_label() -> dict:
    b = settings.llm_backend
    model = {"bedrock": settings.bedrock_model_id,
             "openweights": settings.openweights_model}.get(b, "offline deterministic (proof)")
    return {"backend": b, "model": model, "embed": settings.embed_backend}


def ask(question: str) -> dict:
    rec = SOPCoachAgent().evaluate(Context("ui", {"question": question}, SEED_SOPS))
    if not rec:
        return {"answer": "(no question)", "sources": [], "refused": False}
    r = rec[0]
    return {"answer": r.summary, "sources": r.sources,
            "refused": r.proposed_action.get("type") == "refusal"}


def run_loop() -> dict:
    inputs = {
        "question": "how much rum goes in a mojito?",
        "new_hires": [
            {"id": "H-101", "name": "Ana P.", "role": "f&b",
             "documents": ["passport", "contract", "tax_form"],
             "permit_expiry": "2026-08-20", "start_date": "2026-08-10"},
        ],
        "signals": {"risks": ["Storm warning Thursday PM"],
                    "revenue_alerts": ["Cabanas unbooked this weekend"],
                    "compliance_alerts": ["1 work permit expiring within 30 days"]},
    }
    gate = ApprovalGate()
    result = ExecutionLoop([SOPCoachAgent(), HROnboardingAgent(),
                            ExecutiveIntelligenceAgent()], gate).run(
        Context("sunset-boutique-svg", inputs, SEED_SOPS))
    pending = [p.recommendation.summary for p in gate.queue]
    for i in range(len(gate.queue)):
        gate.resolve(i, ApprovalDecision.APPROVED)
    briefing = next((r.summary for r in result.recommendations
                     if r.agent == "executive_intelligence"), "")
    return {
        "recommendations": [
            {"agent": r.agent, "summary": r.summary.splitlines()[0][:120],
             "risk": r.risk.value, "sources": r.sources}
            for r in result.recommendations],
        "held_for_human": pending,
        "approved_actions": len(pending),
        "briefing": briefing,
        "audit_events": len(result.audit),
    }


PAGE = """<!DOCTYPE html><html lang=en><head><meta charset=UTF-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Velocity Hospitality OS</title><style>
:root{--ink:#0f1a2b;--muted:#5b6b82;--line:#e4e9f1;--bg:#f7f9fc;--card:#fff;--brand:#0e4f8f;--brand2:#12a594;--accent:#c8862b}
*{box-sizing:border-box}body{margin:0;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:var(--ink);background:var(--bg);line-height:1.5}
.wrap{max-width:860px;margin:0 auto;padding:32px 22px 60px}
.eyebrow{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--brand);font-weight:700}
h1{font-size:24px;margin:8px 0 4px}.sub{color:var(--muted);margin:0 0 18px}
.badge{display:inline-flex;gap:8px;align-items:center;background:#eafaf6;color:#0c7a68;border:1px solid #c7ede4;border-radius:999px;padding:5px 12px;font-size:12.5px;font-weight:600}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:20px;margin:16px 0;box-shadow:0 1px 2px rgba(16,32,64,.04)}
h2{font-size:13px;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);margin:0 0 12px}
input[type=text]{width:100%;padding:12px 14px;border:1px solid var(--line);border-radius:10px;font-size:15px}
button{background:var(--brand);color:#fff;border:0;border-radius:10px;padding:11px 18px;font-size:14px;font-weight:600;cursor:pointer;margin-top:10px}
button.ghost{background:#eef4fb;color:var(--brand);border:1px solid #dbe7f6}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin:10px 0}
.chip{font-size:12px;background:#eef4fb;color:var(--brand);border:1px solid #dbe7f6;border-radius:999px;padding:3px 10px;cursor:pointer}
.answer{background:#f4f8fd;border:1px solid #dbe7f6;border-radius:10px;padding:14px;margin-top:12px;white-space:pre-wrap}
.answer.refuse{background:#fff8ef;border-color:#f0dcae;color:#7a5c1e}
.src{font-size:12px;background:#0e4f8f;color:#fff;border-radius:6px;padding:2px 8px;margin-right:6px;display:inline-block;margin-top:8px}
.loop .row{display:flex;gap:8px;align-items:baseline;padding:6px 0;border-bottom:1px solid var(--line);font-size:14px}
.tag{font-size:10px;font-weight:700;text-transform:uppercase;padding:2px 7px;border-radius:5px;white-space:nowrap}
.tag.hold{background:#fdeceb;color:#b42318}.tag.info{background:#eef4fb;color:#0e4f8f}.tag.low{background:#eafaf6;color:#0c7a68}
.foot{color:var(--muted);font-size:12px;margin-top:22px}
.mini{font-size:12px;color:var(--muted)}
</style></head><body><div class=wrap>
<div class=eyebrow>Velocity Hospitality OS · Agentic Execution Layer</div>
<h1>Ask the property's standards</h1>
<p class=sub>Grounded answers from the property's own SOPs — cited, and human-gated for anything consequential.</p>
<div class=badge id=badge>● loading backend…</div>

<div class=card>
  <h2>SOP Coach</h2>
  <input type=text id=q placeholder="e.g. how much rum goes in a mojito?" />
  <div class=chips id=chips></div>
  <button onclick=ask()>Ask</button>
  <div id=ans></div>
</div>

<div class=card>
  <h2>Operations loop (Inputs → Agents → Human approval → Actions → Reporting)</h2>
  <p class=mini>Runs one cycle across three agents on a property's day of inputs. Consequential actions are held for a human.</p>
  <button class=ghost onclick=loop()>Run one operations cycle</button>
  <div id=loop class=loop></div>
</div>

<div class=foot>Model-agnostic &amp; self-hosted. The active model is shown above; swap it (local proof model ↔ open-weights on H200) with zero code changes.</div>
</div><script>
const EX=["how much rum goes in a mojito?","which documents does a new kitchen hire need?","what's our target pour cost?","what is the capital of France?"];
const chips=document.getElementById('chips');EX.forEach(e=>{const c=document.createElement('span');c.className='chip';c.textContent=e;c.onclick=()=>{document.getElementById('q').value=e;ask()};chips.appendChild(c)});
fetch('/api/status').then(r=>r.json()).then(s=>{document.getElementById('badge').innerHTML='● backend: <b>'+s.backend+'</b> &nbsp;·&nbsp; model: <b>'+s.model+'</b>'});
function ask(){const q=document.getElementById('q').value;const a=document.getElementById('ans');a.innerHTML='<div class=mini>thinking…</div>';
 fetch('/api/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:q})}).then(r=>r.json()).then(d=>{
 let s=d.sources.map(x=>'<span class=src>'+x+'</span>').join('');
 a.innerHTML='<div class="answer'+(d.refused?' refuse':'')+'">'+d.answer+'</div>'+(s?'<div>'+s+'</div>':'<div class=mini style=margin-top:8px>no source — refused (grounding guardrail)</div>')})}
function loop(){const L=document.getElementById('loop');L.innerHTML='<div class=mini>running…</div>';
 fetch('/api/loop',{method:'POST'}).then(r=>r.json()).then(d=>{
 let h=d.recommendations.map(r=>{let t=r.risk=='requires_approval'?'<span class="tag hold">held for human</span>':(r.risk=='low'?'<span class="tag low">auto</span>':'<span class="tag info">info</span>');return '<div class=row>'+t+'<span>'+r.summary+'</span></div>'}).join('');
 h+='<div class=row style=border:0><b>'+d.approved_actions+'</b>&nbsp;action(s) executed after human approval &nbsp;·&nbsp; '+d.audit_events+' audit events logged</div>';
 L.innerHTML=h})}
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
    print(f"Velocity Hospitality OS UI → http://localhost:{PORT}")
    print(f"  backend: {info['backend']}   model: {info['model']}")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
