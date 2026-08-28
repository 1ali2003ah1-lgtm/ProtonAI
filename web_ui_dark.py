"""
ProtonAI - Dark Luxury UI (نسخة داكنة فاخرة)
تصميم glassmorphism داكن (RTL, WCAG AA):
خلفية navy عميقة + بطاقات زجاجية + تدرج neon هادئ + RAG (لون+أيقونة+نص)
+ timeline بصمات + درع سلامة + إقرار إجباري.
يعيد استخدام بيانات web_ui_premium (DOSSIERS).
تشغيل: uvicorn web_ui_dark:app
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

from cohort_analytics import analyze
from dossier_verify import verify_dossier
from web_ui_premium import DOSSIERS

ACKS = []

UI = """<!DOCTYPE html>
<html lang="ar" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ProtonAI — Dark</title>
<style>
:root{--bg:#0B1220;--surface:rgba(255,255,255,.06);--line:rgba(255,255,255,.12);
--ink:#E6ECF5;--sub:#9AA7BD;--accent:#22D3EE;--accent2:#818CF8;
--green:#4ADE80;--amber:#FBBF24;--red:#F87171;--focus:#60A5FA;--r:16px}
*{box-sizing:border-box}body{margin:0;font:15px/1.6 "IBM Plex Sans Arabic",system-ui,sans-serif;
color:var(--ink);background:radial-gradient(1200px 600px at 80% -10%,rgba(34,211,238,.15),transparent),
radial-gradient(900px 500px at 10% 110%,rgba(129,140,248,.15),transparent),var(--bg)}
a.skip{position:absolute;right:-999px;top:0;background:var(--accent);color:#001018;padding:12px;z-index:99}a.skip:focus{right:8px}
main{max-width:1000px;margin:0 auto;padding:28px}
.glass{background:var(--surface);border:1px solid var(--line);border-radius:var(--r);
backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);padding:22px;margin-bottom:20px}
.hero h1{margin:0;font-size:26px;background:linear-gradient(90deg,var(--accent),var(--accent2));
-webkit-background-clip:text;background-clip:text;color:transparent}
.hero p{color:var(--sub);margin:6px 0 0}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:16px}
.kpi .v{font-size:30px;font-weight:700;font-variant-numeric:tabular-nums}
.kpi .l{color:var(--sub);font-size:13px}
table{width:100%;border-collapse:collapse}th,td{padding:12px;border-bottom:1px solid var(--line);text-align:right}
.pill{display:inline-flex;gap:6px;align-items:center;padding:4px 12px;border-radius:999px;font-weight:600;border:2px solid}
.p-PROCEED{color:var(--green);border-color:var(--green)}
.p-REVIEW{color:var(--amber);border-color:var(--amber)}
.p-STOP{color:var(--red);border-color:var(--red)}
button.cta{min-height:44px;padding:10px 22px;border:0;border-radius:12px;
background:linear-gradient(90deg,var(--accent),var(--accent2));color:#001018;font-weight:700;cursor:pointer}
button:focus-visible{outline:3px solid var(--focus);outline-offset:2px}
.timeline{list-style:none;padding:0}.timeline li{display:flex;gap:10px;padding:8px 0;border-bottom:1px dashed var(--line)}
.timeline .h{font-family:monospace;color:var(--sub);font-size:12px}
.shield.ok{color:var(--green)}.shield.bad{color:var(--red)}
.tiles{display:flex;gap:14px;flex-wrap:wrap}.tile{border:1px solid var(--line);border-radius:12px;padding:12px;min-width:110px}.tile .v{font-size:22px;font-weight:700}
details{margin:14px 0;border:1px solid var(--line);border-radius:12px;padding:12px}
dialog{border:1px solid var(--line);border-radius:var(--r);background:#0F1A30;color:var(--ink);padding:26px;max-width:480px}
label{display:block;margin:14px 0}input[type=text]{width:100%;min-height:44px;padding:10px;border:2px solid var(--line);border-radius:12px;background:transparent;color:var(--ink)}
.err{color:var(--red);font-weight:700}
</style></head><body>
<a class="skip" href="#main">تخطَّ إلى المحتوى</a>
<main id="main">
<div class="glass hero"><h1>🧬 ProtonAI — منصة القرار السريري</h1>
<p>ذكاء موثق • سلامة أولاً • إقرار بشري إجباري</p></div>
<div class="kpis" id="kpis"></div>
<div class="glass" style="margin-top:20px"><h2>الحالات</h2>
<table aria-label="الحالات"><thead><tr><th>الحالة</th><th>الموقع</th><th>القرار</th><th></th></tr></thead>
<tbody id="rows"></tbody></table></div>
<section id="detail" hidden aria-live="polite"></section>
</main>
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
  <div class="glass kpi"><div class="v">${c.total}</div><div class="l">الحالات</div></div>
  <div class="glass kpi"><div class="v">${(c.stop_rate*100).toFixed(0)}%</div><div class="l">الإيقاف</div></div>
  <div class="glass kpi"><div class="v">${(c.mean_agreement*100).toFixed(0)}%</div><div class="l">الإجماع</div></div>
  <div class="glass kpi"><div class="v">${(c.favors_proton_rate*100).toFixed(0)}%</div><div class="l">البروتون</div></div>`;
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
 el.innerHTML=`<div class="glass">
  <span class="pill p-${d.final}" style="font-size:18px">${IC[d.final]} ${d.final}</span>
  <span class="shield ${v.valid?'ok':'bad'}">${v.valid?'🔒 سجل سليم':'⛔ سجل مكسور'}</span>
  <div class="tiles" style="margin-top:14px">
   <div class="tile"><div class="v">${d.synthesis.board_agreement.toFixed(2)}</div>الإجماع</div>
   <div class="tile"><div class="v">${d.synthesis.evidence_count}</div>أدلة</div>
   <div class="tile"><div class="v">${d.synthesis.risk_count}</div>مخاطر</div></div>
  <details><summary>السرد السريري</summary><pre style="white-space:pre-wrap">${d.narrative}</pre></details>
  <ul class="timeline">${d.stages.map(s=>`<li>${s.name} <span class="h">${s.hash.slice(0,10)}…</span></li>`).join("")}</ul>
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
    app = FastAPI(title="ProtonAI Dark")

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
