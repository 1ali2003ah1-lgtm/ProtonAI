"""
ProtonAI - Premium Enterprise UI
واجهة مؤسسية فخمة (RTL, WCAG 2.2 AA):
sidebar داكن + hero متدرج + KPI cards + RAG (لون+أيقونة+نص) +
timeline لسلسلة البصمات + درع سلامة + إقرار بشري إجباري.
تشغيل (لابتوب): pip install fastapi uvicorn ثم uvicorn web_ui_premium:app
"""

from dataclasses import asdict

try:
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse
    from pydantic import BaseModel
    FASTAPI_AVAILABLE = True
except Exception:  # pragma: no cover
    FastAPI = None
    HTMLResponse = None
    BaseModel = object
    FASTAPI_AVAILABLE = False

from case_orchestrator import CaseOrchestrator, CaseSpec
from cohort_analytics import analyze
from dossier_verify import verify_dossier

ORCH = CaseOrchestrator()
SPECS = [
    CaseSpec("P-001", "prostate", doses=[2.0] * 10,
             scanners={"CT-A": [0.02]}, measured=[2, 2], planned=[2, 2],
             achieved_oars={"rectum_V70": 10}),
    CaseSpec("P-002", "CNS_brain_spine", dice=0.88, doses=[2.0] * 10,
             scanners={"CT-A": [0.02]}, measured=[2, 2], planned=[2, 2],
             achieved_oars={"cord_Dmax": 30}),
    CaseSpec("P-003", "lung_pleura", status="RED", doses=[2.0] * 10,
             scanners={"CT-B": [0.05]}, measured=[2, 3], planned=[2, 2],
             achieved_oars={"lung_V20": 20}),
]
DOSSIERS = {s.case_id: ORCH.run(s) for s in SPECS}
ACKS = []

UI = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ProtonAI — منصة القرار السريري</title>
<style>
:root{--bg:#F6F8FB;--surface:#fff;--ink:#0B1526;--sub:#51607A;--line:#E3E9F2;
--accent:#0E7490;--accent2:#4338CA;--green:#15803D;--amber:#B45309;--red:#B91C1C;
--focus:#1D4ED8;--side:#0B1526;--side-ink:#E6ECF5;--r:14px}
*{box-sizing:border-box}body{margin:0;font:15px/1.6 "IBM Plex Sans Arabic",system-ui,sans-serif;background:var(--bg);color:var(--ink)}
a.skip{position:absolute;right:-999px;top:0;background:var(--accent);color:#fff;padding:12px;z-index:99}a.skip:focus{right:8px}
.shell{display:flex;min-height:100vh}
aside{width:230px;background:var(--side);color:var(--side-ink);padding:20px;position:sticky;top:0;height:100vh}
.logo{font-size:20px;font-weight:700;margin-bottom:24px}
nav button{display:block;width:100%;text-align:right;background:none;border:0;color:var(--side-ink);padding:12px;border-radius:10px;font-size:15px;cursor:pointer;margin-bottom:4px}
nav button:hover,nav button[aria-current]{background:rgba(255,255,255,.12)}
main{flex:1;padding:28px;max-width:1100px}
.hero{background:linear-gradient(135deg,var(--accent),var(--accent2));color:#fff;border-radius:var(--r);padding:26px;margin-bottom:24px}
.hero h1{margin:0 0 6px;font-size:24px}.hero p{margin:0;opacity:.95}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:16px;margin-bottom:24px}
.kpi{background:var(--surface);border:1px solid var(--line);border-radius:var(--r);padding:18px;box-shadow:0 6px 20px rgba(16,24,40,.06)}
.kpi .v{font-size:30px;font-weight:700;font-variant-numeric:tabular-nums}
.kpi .l{color:var(--sub);font-size:13px}
.card{background:var(--surface);border:1px solid var(--line);border-radius:var(--r);padding:20px;margin-bottom:20px;box-shadow:0 6px 20px rgba(16,24,40,.06)}
table{width:100%;border-collapse:collapse}th,td{padding:12px;border-bottom:1px solid var(--line);text-align:right}
.pill{display:inline-flex;gap:6px;align-items:center;padding:4px 12px;border-radius:999px;font-weight:600;border:2px solid}
.p-PROCEED{color:var(--green);border-color:var(--green);background:#F0FDF4}
.p-REVIEW{color:var(--amber);border-color:var(--amber);background:#FFFBEB}
.p-STOP{color:var(--red);border-color:var(--red);background:#FEF2F2}
button.cta{min-height:44px;padding:10px 20px;border:0;border-radius:10px;background:var(--accent);color:#fff;font-size:15px;cursor:pointer}
button:focus-visible,input:focus-visible{outline:3px solid var(--focus);outline-offset:2px}
.timeline{list-style:none;padding:0;margin:16px 0}
.timeline li{display:flex;gap:12px;align-items:center;padding:10px 0;border-bottom:1px dashed var(--line)}
.timeline .h{font-family:monospace;color:var(--sub);font-size:12px}
.shield{display:inline-flex;gap:8px;align-items:center;font-weight:700}
.shield.ok{color:var(--green)}.shield.bad{color:var(--red)}
dialog{border:0;border-radius:var(--r);padding:28px;max-width:480px;box-shadow:0 20px 60px rgba(0,0,0,.3)}
dialog::backdrop{background:rgba(11,21,38,.6)}
label{display:block;margin:14px 0}input[type=text]{width:100%;min-height:44px;padding:10px;border:2px solid var(--line);border-radius:10px}
.err{color:var(--red);font-weight:700}
.tiles{display:flex;gap:14px;flex-wrap:wrap}.tile{border:1px solid var(--line);border-radius:12px;padding:12px;min-width:110px}.tile .v{font-size:22px;font-weight:700}
details{margin:14px 0;border:1px solid var(--line);border-radius:12px;padding:12px}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
</style></head>
<body>
<a class="skip" href="#main">تخطَّ إلى المحتوى</a>
<div class="shell">
<aside><div class="logo">🧬 ProtonAI</div>
<nav aria-label="التنقل الرئيسي">
<button aria-current="page">لوحة المؤشرات</button>
<button>الحالات</button><button>الفيزياء</button>
<button>مجلس الورم</button><button>التدقيق</button>
</nav></aside>
<main id="main">
<div class="hero"><h1>منصة القرار السريري للعلاج بالبروتون</h1>
<p>ذكاء سريري موثق • سلامة أولاً • إقرار بشري إجباري</p></div>
<div class="kpis" id="kpis"></div>
<div class="card"><h2>الحالات</h2>
<table aria-label="قائمة الحالات"><thead><tr><th>الحالة</th><th>الموقع</th><th>القرار</th><th></th></tr></thead>
<tbody id="rows"></tbody></table></div>
<section id="detail" hidden aria-live="polite"></section>
</main></div>
<dialog id="ack" aria-labelledby="ackT"><h2 id="ackT">إقرار المراجعة</h2>
<p>هذا دعم قرار فقط؛ القرار السريري مسؤوليتك بعد المراجعة.</p>
<label><input type="checkbox" id="ackChk"> أُقرّ أنني راجعت التوصية وأتحمل القرار النهائي</label>
<label>اسم المُقِرّ <input type="text" id="ackName"></label>
<p class="err" id="ackErr" hidden>فعّل الإقرار وأدخل الاسم أولاً.</p>
<p><button class="cta" id="ackOk">تأكيد الإقرار</button></p></dialog>
<div aria-live="assertive" id="live"></div>
<script>
const IC={PROCEED:"✅",REVIEW:"⚠️",STOP:"⛔"};
async function boot(){
 const c=await(await fetch("/api/cohort")).json();
 document.getElementById("kpis").innerHTML=`
  <div class="kpi"><div class="v">${c.total}</div><div class="l">إجمالي الحالات</div></div>
  <div class="kpi"><div class="v">${(c.stop_rate*100).toFixed(0)}%</div><div class="l">معدل الإيقاف</div></div>
  <div class="kpi"><div class="v">${(c.mean_agreement*100).toFixed(0)}%</div><div class="l">متوسط الإجماع</div></div>
  <div class="kpi"><div class="v">${(c.favors_proton_rate*100).toFixed(0)}%</div><div class="l">تفضيل البروتون</div></div>`;
 const cs=await(await fetch("/api/cases")).json();
 document.getElementById("rows").innerHTML=cs.map(x=>
  `<tr><td>${x.case_id}</td><td>${x.site}</td>
   <td><span class="pill p-${x.final}">${IC[x.final]} ${x.final}</span></td>
   <td><button class="cta" data-id="${x.case_id}">فتح</button></td></tr>`).join("");
 document.querySelectorAll("#rows button").forEach(b=>b.onclick=()=>open(b.dataset.id));
}
async function open(id){
 const d=await(await fetch("/api/dossier/"+id)).json();
 const v=await(await fetch("/api/verify/"+id)).json();
 const el=document.getElementById("detail");el.hidden=false;
 el.innerHTML=`<div class="card">
  <div class="pill p-${d.final}" style="font-size:18px">${IC[d.final]} القرار: ${d.final}</div>
  <span class="shield ${v.valid?'ok':'bad'}">${v.valid?'🔒 سجل سليم':'⛔ سجل مكسور'}</span>
  <div class="tiles" style="margin-top:16px">
   <div class="tile"><div class="v">${d.synthesis.board_agreement.toFixed(2)}</div>الإجماع</div>
   <div class="tile"><div class="v">${d.synthesis.evidence_count}</div>أدلة</div>
   <div class="tile"><div class="v">${d.synthesis.risk_count}</div>مخاطر</div>
  </div>
  <details><summary>لماذا هذا القرار؟ (السرد السريري)</summary><pre style="white-space:pre-wrap">${d.narrative}</pre></details>
  <h3>سلسلة البصمات (hash chain)</h3>
  <ul class="timeline">${d.stages.map(s=>`<li><span class="pill p-${s.status==='OK'?'PROCEED':s.status}">${s.status}</span> ${s.name} <span class="h">${s.hash.slice(0,10)}…</span></li>`).join("")}</ul>
  <button class="cta" id="ackBtn">أُقرّ بالمراجعة وأتحمل القرار النهائي</button></div>`;
 document.getElementById("ackBtn").onclick=()=>{
  const dlg=document.getElementById("ack");dlg.showModal();
  document.getElementById("ackChk").focus();
  document.getElementById("ackOk").onclick=async()=>{
   if(!document.getElementById("ackChk").checked||!document.getElementById("ackName").value.trim()){
    document.getElementById("ackErr").hidden=false;return;}
   await fetch("/api/ack",{method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify({case_id:id,name:document.getElementById("ackName").value})});
   dlg.close();document.getElementById("live").textContent="تم تسجيل الإقرار.";};};
 el.scrollIntoView();
}
boot();
</script></body></html>"""

if FASTAPI_AVAILABLE:
    app = FastAPI(title="ProtonAI Premium")

    class Ack(BaseModel):
        case_id: str
        name: str

    @app.get("/", response_class=HTMLResponse)
    def index():
        return UI

    @app.get("/api/cases")
    def cases():
        return [{"case_id": d.case_id, "site": d.site, "final": d.final}
                for d in DOSSIERS.values()]

    @app.get("/api/cohort")
    def cohort():
        return asdict(analyze(list(DOSSIERS.values())))

    @app.get("/api/dossier/{cid}")
    def dossier(cid: str):
        d = DOSSIERS.get(cid)
        if not d:
            return {"error": "not found"}
        return {"final": d.final, "narrative": d.combined["narrative"],
                "synthesis": d.combined["synthesis"],
                "stages": [{"name": s.name, "status": s.status,
                            "hash": s.hash} for s in d.stages]}

    @app.get("/api/verify/{cid}")
    def verify(cid: str):
        d = DOSSIERS.get(cid)
        return verify_dossier(d) if d else {"valid": False}

    @app.post("/api/ack")
    def ack(a: Ack):
        ACKS.append(a.dict())
        return {"ok": True}
