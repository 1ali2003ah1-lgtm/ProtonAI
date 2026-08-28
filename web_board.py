"""
ProtonAI - Interactive Tumor Board (واجهة مجلس الورم)
جلسة مجلس ورم حية وتفاعلية بنفس اللغة البصرية الفخمة:
- بطاقات مشاركين بأدوار متعددة.
- عدّاد إجماع + آراء أقلية موثقة + نقض سلامة.
- إضافة رأي لحظياً يعيد حساب القرار.
تشغيل: uvicorn web_board:app
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

from tumor_board import Opinion, TumorBoard

BOARDS = {"P-001": TumorBoard("P-001")}
for o in [Opinion("د. سارة", "oncologist", "PROCEED", 0.9, "تغطية ممتازة"),
          Opinion("د. ليث", "physicist", "PROCEED", 0.85, "المدى ضمن الهامش"),
          Opinion("د. ميس", "radiologist", "REVIEW", 0.7, "أفضّل مراجعة الصورة")]:
    BOARDS["P-001"].add(o)

UI = """<!DOCTYPE html>
<html lang="ar" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ProtonAI — مجلس الورم</title>
<style>
:root{--bg:#F6F8FB;--surface:#fff;--ink:#0B1526;--sub:#51607A;--line:#E3E9F2;
--accent:#0E7490;--accent2:#4338CA;--green:#15803D;--amber:#B45309;--red:#B91C1C;--focus:#1D4ED8;--r:14px}
*{box-sizing:border-box}body{margin:0;font:15px/1.6 "IBM Plex Sans Arabic",system-ui,sans-serif;background:var(--bg);color:var(--ink)}
main{max-width:900px;margin:0 auto;padding:28px}
.hero{background:linear-gradient(135deg,var(--accent),var(--accent2));color:#fff;border-radius:var(--r);padding:24px;margin-bottom:24px}
.hero h1{margin:0;font-size:22px}
.card{background:var(--surface);border:1px solid var(--line);border-radius:var(--r);padding:20px;margin-bottom:20px;box-shadow:0 6px 20px rgba(16,24,40,.06)}
.parts{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px}
.part{border:1px solid var(--line);border-radius:12px;padding:14px}
.part .role{color:var(--sub);font-size:13px}
.pill{display:inline-flex;gap:6px;align-items:center;padding:4px 12px;border-radius:999px;font-weight:600;border:2px solid}
.p-PROCEED{color:var(--green);border-color:var(--green);background:#F0FDF4}
.p-REVIEW{color:var(--amber);border-color:var(--amber);background:#FFFBEB}
.p-STOP{color:var(--red);border-color:var(--red);background:#FEF2F2}
.meter{height:12px;border-radius:999px;background:var(--line);overflow:hidden;margin:10px 0}
.meter>div{height:100%;background:linear-gradient(90deg,var(--accent),var(--accent2))}
.banner{border-radius:12px;padding:16px;border:3px solid;font-size:18px;font-weight:700}
.b-PROCEED{border-color:var(--green);background:#F0FDF4}
.b-REVIEW{border-color:var(--amber);background:#FFFBEB}
.b-STOP{border-color:var(--red);background:#FEF2F2}
form{display:grid;gap:12px}select,input{min-height:44px;padding:10px;border:2px solid var(--line);border-radius:10px}
button.cta{min-height:44px;padding:10px 20px;border:0;border-radius:10px;background:var(--accent);color:#fff;font-size:15px;cursor:pointer}
button:focus-visible,select:focus-visible{outline:3px solid var(--focus);outline-offset:2px}
.dissent{border-right:4px solid var(--amber);padding:8px 12px;background:#FFFBEB;border-radius:8px;margin:8px 0}
</style></head><body><main>
<div class="hero"><h1>🏥 مجلس الورم — الحالة P-001</h1></div>
<div class="card"><h2>المشاركون</h2><div class="parts" id="parts"></div></div>
<div class="card"><h2>الإجماع</h2><div class="meter"><div id="bar"></div></div>
<p id="agreeTxt"></p><div id="dissent"></div></div>
<div class="card" id="decisionCard"></div>
<div class="card"><h2>إضافة رأي</h2>
<form id="f"><select id="role" aria-label="الدور">
<option value="oncologist">أورام</option><option value="physicist">فيزياء</option>
<option value="surgeon">جراحة</option><option value="radiologist">أشعة</option></select>
<select id="rec" aria-label="التوصية">
<option value="PROCEED">PROCEED</option><option value="REVIEW">REVIEW</option>
<option value="STOP">STOP</option></select>
<button class="cta" type="submit">إدراج الرأي</button></form></div>
<div aria-live="assertive" id="live"></div></main>
<script>
const IC={PROCEED:"✅",REVIEW:"⚠️",STOP:"⛔"};
async function load(){
 const b=await(await fetch("/api/board/P-001")).json();
 document.getElementById("parts").innerHTML=b.participants.map(p=>
  `<div class="part"><b>${p.participant}</b><div class="role">${p.role}</div>
   <span class="pill p-${p.recommendation}">${IC[p.recommendation]} ${p.recommendation}</span></div>`).join("");
 document.getElementById("bar").style.width=(b.record.agreement_ratio*100)+"%";
 document.getElementById("agreeTxt").textContent=
  `نسبة الإجماع: ${(b.record.agreement_ratio*100).toFixed(0)}% — `+
  (b.record.consensus?"تم بلوغ الإجماع":"لم يُبلغ الإجماع بعد");
 document.getElementById("dissent").innerHTML=b.record.dissent.map(d=>
  `<div class="dissent">رأي أقلية: ${d.participant} (${d.recommendation})</div>`).join("");
 const d=b.record.decision||"—";
 document.getElementById("decisionCard").innerHTML=
  `<div class="banner b-${d==='—'?'REVIEW':d}">${IC[d]||"❓"} قرار المجلس: ${d}</div>
   <p>${b.record.reason}</p>`;
}
document.getElementById("f").onsubmit=async e=>{
 e.preventDefault();
 await fetch("/api/board/P-001/opinion",{method:"POST",
  headers:{"Content-Type":"application/json"},
  body:JSON.stringify({participant:"د. جديد",
   role:document.getElementById("role").value,
   recommendation:document.getElementById("rec").value,confidence:0.8})});
 document.getElementById("live").textContent="تم إدراج الرأي وإعادة الحساب.";
 load();};
load();
</script></body></html>"""

if FASTAPI_AVAILABLE:
    app = FastAPI(title="ProtonAI Board")

    class OpIn(BaseModel):
        participant: str
        role: str
        recommendation: str
        confidence: float = 0.8

    def _payload(b: TumorBoard):
        rec = b.decide()
        return {"participants": [
                    {"participant": o.participant, "role": o.role,
                     "recommendation": o.recommendation}
                    for o in b.opinions],
                "record": {"decision": rec.decision,
                           "consensus": rec.consensus,
                           "agreement_ratio": rec.agreement_ratio,
                           "reason": rec.reason,
                           "dissent": [{"participant": d.participant,
                                        "recommendation": d.recommendation}
                                       for d in rec.dissent]}}

    @app.get("/", response_class=HTMLResponse)
    def index():
        return UI

    @app.get("/api/board/{cid}")
    def board(cid: str):
        b = BOARDS.get(cid)
        return _payload(b) if b else {"error": "not found"}

    @app.post("/api/board/{cid}/opinion")
    def add_opinion(cid: str, o: OpIn):
        b = BOARDS.get(cid)
        if not b:
            return {"error": "not found"}
        b.add(Opinion(o.participant, o.role, o.recommendation, o.confidence))
        return _payload(b)
