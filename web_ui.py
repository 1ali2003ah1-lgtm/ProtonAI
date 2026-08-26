"""
ProtonAI - Web UI (واجهة سريرية آمنة)
RTL عالية التباين (WCAG 2.2 AA): لوحة RAG + تقرير حالة + إقرار إجباري.
تعمل إن وُجدت fastapi؛ والـ HTML قابل للاختبار بدونها.
تشغيل (لابتوب): pip install fastapi uvicorn ثم uvicorn web_ui:app
"""

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

from clinical_report import build_report

CASES = [
    build_report("P-001", "prostate", 0.92, 0.02),
    build_report("P-002", "CNS_brain_spine", 0.88, 0.02),
    build_report("P-003", "lung_pleura", 0.90, 0.02, status="RED"),
]
ACKS = []

UI_HTML = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ProtonAI — دعم قرار البروتون</title>
<style>
:root{--ink:#0F172A;--sub:#475569;--bg:#FFF;--soft:#F8FAFC;--line:#CBD5E1;
--act:#0F766E;--green:#15803D;--amber:#B45309;--red:#B91C1C;--focus:#1D4ED8}
*{box-sizing:border-box}
body{margin:0;font:16px/1.6 system-ui,sans-serif;color:var(--ink);background:var(--bg)}
a.skip{position:absolute;right:-999px;top:0;background:var(--act);color:#fff;padding:12px}
a.skip:focus{right:8px}
header{padding:16px 24px;border-bottom:2px solid var(--line);background:var(--soft)}
h1{font-size:20px;margin:0}
main{max-width:960px;margin:0 auto;padding:24px}
.counters{display:flex;gap:16px;flex-wrap:wrap}
.counter{flex:1;min-width:140px;border:2px solid var(--line);border-radius:8px;padding:16px;text-align:center}
.counter .num{font-size:32px;font-variant-numeric:tabular-nums}
.c-green{border-color:var(--green)}.c-amber{border-color:var(--amber)}.c-red{border-color:var(--red)}
table{width:100%;border-collapse:collapse;margin-top:24px}
th,td{padding:12px;border-bottom:1px solid var(--line);text-align:right}
button{min-height:44px;min-width:44px;padding:10px 16px;border-radius:6px;border:2px solid transparent;background:var(--act);color:#fff;font-size:16px;cursor:pointer}
button:focus-visible,input:focus-visible{outline:3px solid var(--focus);outline-offset:2px}
button.secondary{background:#fff;color:var(--act);border-color:var(--act)}
.banner{border-radius:8px;padding:16px;margin:16px 0;border:3px solid;font-size:18px}
.b-PROCEED{border-color:var(--green);background:#F0FDF4}
.b-REVIEW{border-color:var(--amber);background:#FFFBEB}
.b-STOP{border-color:var(--red);background:#FEF2F2}
.tiles{display:flex;gap:16px;flex-wrap:wrap}
.tile{border:2px solid var(--line);border-radius:8px;padding:12px;min-width:120px}
.tile .v{font-size:24px;font-variant-numeric:tabular-nums}
details{margin:16px 0;border:1px solid var(--line);border-radius:8px;padding:12px}
dialog{border:3px solid var(--red);border-radius:8px;padding:24px;max-width:480px}
label{display:block;margin:12px 0}
input[type=text]{width:100%;min-height:44px;padding:8px;border:2px solid var(--line);border-radius:6px}
.err{color:var(--red);font-weight:bold}
footer{padding:16px 24px;color:var(--sub);border-top:1px solid var(--line)}
</style>
</head>
<body>
<a class="skip" href="#main">تخطَّ إلى المحتوى</a>
<header><h1>🧬 ProtonAI — دعم قرار العلاج بالبروتون</h1></header>
<main id="main">
 <div class="counters" id="counters"></div>
 <table aria-label="قائمة الحالات">
  <thead><tr><th>الحالة</th><th>الموقع</th><th>القرار</th><th></th></tr></thead>
  <tbody id="rows"></tbody>
 </table>
 <section id="detail" hidden aria-live="polite"></section>
</main>
<dialog id="ack" aria-labelledby="ackTitle">
 <h2 id="ackTitle">إقرار المراجعة</h2>
 <p>هذا دعم قرار فقط؛ القرار السريري مسؤوليتك بعد المراجعة.</p>
 <label><input type="checkbox" id="ackChk"> أُقرّ أنني راجعت التوصية وأتحمل القرار النهائي</label>
 <label>اسم المُقِرّ <input type="text" id="ackName"></label>
 <p class="err" id="ackErr" hidden>فعّل الإقرار وأدخل الاسم أولاً.</p>
 <p><button id="ackOk">تأكيد الإقرار</button>
 <button class="secondary" id="ackNo">إلغاء</button></p>
</dialog>
<div aria-live="assertive" id="live"></div>
<footer>منصة بحثية — ليست جهازاً طبياً. RED = إيقاف + مراجعة إجبارية.</footer>
<script>
const ICON={PROCEED:"✅",REVIEW:"⚠️",STOP:"⛔"};
async function load(){
 const cs=await (await fetch("/api/cases")).json();
 const n={PROCEED:0,REVIEW:0,STOP:0};
 cs.forEach(c=>n[c.decision]++);
 document.getElementById("counters").innerHTML=
  ["PROCEED","REVIEW","STOP"].map(k=>
   `<div class="counter c-${k.toLowerCase()}"><div class="num">${n[k]}</div>${ICON[k]} ${k}</div>`).join("");
 document.getElementById("rows").innerHTML=cs.map(c=>
  `<tr><td>${c.case_id}</td><td>${c.site}</td><td>${ICON[c.decision]} ${c.decision}</td>
   <td><button data-id="${c.case_id}">مراجعة</button></td></tr>`).join("");
 document.querySelectorAll("#rows button").forEach(b=>b.onclick=()=>openCase(b.dataset.id));
}
async function openCase(id){
 const r=await (await fetch("/api/case/"+id)).json();
 const d=document.getElementById("detail"); d.hidden=false;
 d.innerHTML=`<div class="banner b-${r.decision}">${ICON[r.decision]} القرار: ${r.decision}</div>
  <div class="tiles">
   <div class="tile"><div class="v">${r.metrics.dice.toFixed(2)}</div>Dice</div>
   <div class="tile"><div class="v">${r.metrics.ece.toFixed(2)}</div>ECE</div>
   <div class="tile"><div class="v">${r.range_margin_mm.toFixed(1)} مم</div>هامش المدى</div>
  </div>
  <details><summary>لماذا هذا القرار؟</summary><p>${r.reasons.join("؛ ")||"كل المؤشرات ضمن الأهداف."}</p></details>
  <button id="ackBtn">أُقرّ بالمراجعة وأتحمل القرار النهائي</button>`;
 document.getElementById("ackBtn").onclick=()=>{
  const dlg=document.getElementById("ack"); dlg.showModal();
  document.getElementById("ackChk").focus();
  document.getElementById("ackOk").onclick=async()=>{
   const chk=document.getElementById("ackChk").checked;
   const nm=document.getElementById("ackName").value.trim();
   if(!chk||!nm){document.getElementById("ackErr").hidden=false;return;}
   await fetch("/api/ack",{method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify({case_id:id,name:nm})});
   dlg.close();
   document.getElementById("live").textContent="تم تسجيل الإقرار في سجل التدقيق.";
  };
  document.getElementById("ackNo").onclick=()=>dlg.close();
 };
 d.scrollIntoView();
}
load();
</script>
</body>
</html>"""

if FASTAPI_AVAILABLE:
    app = FastAPI(title="ProtonAI UI")

    class Ack(BaseModel):
        case_id: str
        name: str

    @app.get("/", response_class=HTMLResponse)
    def index():
        return UI_HTML

    @app.get("/api/cases")
    def cases():
        return [{k: c[k] for k in ("case_id", "site", "decision")} for c in CASES]

    @app.get("/api/case/{cid}")
    def case(cid: str):
        for c in CASES:
            if c["case_id"] == cid:
                return c
        return {"error": "not found"}

    @app.post("/api/ack")
    def ack(a: Ack):
        ACKS.append({"case_id": a.case_id, "name": a.name})
        return {"ok": True, "logged": True}
