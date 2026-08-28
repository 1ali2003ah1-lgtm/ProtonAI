"""
ProtonAI - Governance Dashboard (واجهة برج المراقبة)
لوحة قيادة تنفيذية (RTL, WCAG AA):
- درع وضعية كبير (RAG + أيقونة + نص).
- بطاقات تنبيهات مُصعَّدة (شدة بلون+أيقونة+نص).
- مؤشرات حية (أسطول/انجراف/سجلات/إيقاف/إجماع).
- سرد تنفيذي تلقائي + زر تشغيل دورة.
تشغيل: uvicorn web_governance:app
"""

from dataclasses import asdict

try:
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse
    FASTAPI_AVAILABLE = True
except Exception:  # pragma: no cover
    FastAPI = None
    HTMLResponse = None
    FASTAPI_AVAILABLE = False

from control_tower import ControlTower
from web_ui_premium import DOSSIERS

SCANNERS = {"CT-A": [0.02], "CT-B": [0.045]}
DRIFT = "GREEN"

UI = """<!DOCTYPE html>
<html lang="ar" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ProtonAI — الحوكمة</title>
<style>
:root{--bg:#F6F8FB;--surface:#fff;--ink:#0B1526;--sub:#51607A;--line:#E3E9F2;
--accent:#0E7490;--accent2:#4338CA;--green:#15803D;--amber:#B45309;--red:#B91C1C;--focus:#1D4ED8;--r:14px}
*{box-sizing:border-box}body{margin:0;font:15px/1.6 "IBM Plex Sans Arabic",system-ui,sans-serif;background:var(--bg);color:var(--ink)}
main{max-width:960px;margin:0 auto;padding:28px}
.hero{background:linear-gradient(135deg,var(--accent),var(--accent2));color:#fff;border-radius:var(--r);padding:24px;margin-bottom:24px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px}
.hero h1{margin:0;font-size:22px}
.shield{font-size:20px;font-weight:800;padding:10px 22px;border-radius:999px;border:3px solid;background:#fff}
.s-GREEN{color:var(--green);border-color:var(--green)}
.s-AMBER{color:var(--amber);border-color:var(--amber)}
.s-RED{color:var(--red);border-color:var(--red)}
.card{background:var(--surface);border:1px solid var(--line);border-radius:var(--r);padding:20px;margin-bottom:20px;box-shadow:0 6px 20px rgba(16,24,40,.06)}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px}
.tile{border:1px solid var(--line);border-radius:12px;padding:14px}.tile .v{font-size:24px;font-weight:700;font-variant-numeric:tabular-nums}.tile .l{color:var(--sub);font-size:13px}
.alert{border-radius:12px;padding:14px;margin-bottom:12px;border:2px solid;display:flex;gap:12px;align-items:flex-start}
.a-HIGH{border-color:var(--red);background:#FEF2F2}
.a-MEDIUM{border-color:var(--amber);background:#FFFBEB}
.a-LOW{border-color:var(--green);background:#F0FDF4}
.alert .sev{font-weight:800}
button.cta{min-height:44px;padding:10px 22px;border:0;border-radius:10px;background:#fff;color:var(--accent2);font-weight:700;cursor:pointer}
button:focus-visible{outline:3px solid var(--focus);outline-offset:2px}
.exec{white-space:pre-wrap;color:var(--sub)}
</style></head><body><main>
<div class="hero"><h1>🛰️ برج المراقبة — الحوكمة الذاتية</h1>
<span class="shield" id="posture">…</span></div>
<div class="card"><h2>المؤشرات الحية</h2><div class="tiles" id="tiles"></div></div>
<div class="card"><h2>التنبيهات المُصعَّدة</h2><div id="alerts"></div></div>
<div class="card"><h2>السرد التنفيذي</h2><p class="exec" id="exec"></p>
<button class="cta" id="run">🔄 تشغيل دورة فحص</button></div>
<div aria-live="assertive" id="live"></div></main>
<script>
const IC={GREEN:"✅",AMBER:"⚠️",RED:"⛔"};
const SV={HIGH:"🔴",MEDIUM:"🟠",LOW:"🟢"};
async function load(){
 const g=await(await fetch("/api/governance")).json();
 const p=document.getElementById("posture");
 p.textContent=`${IC[g.posture]} ${g.posture}`;
 p.className="shield s-"+g.posture;
 document.getElementById("tiles").innerHTML=`
  <div class="tile"><div class="v">${g.metrics.fleet}</div><div class="l">الأسطول</div></div>
  <div class="tile"><div class="v">${g.metrics.drift}</div><div class="l">الانجراف</div></div>
  <div class="tile"><div class="v">${g.metrics.invalid}</div><div class="l">سجلات غير سليمة</div></div>
  <div class="tile"><div class="v">${(g.metrics.stop_rate*100).toFixed(0)}%</div><div class="l">معدل الإيقاف</div></div>
  <div class="tile"><div class="v">${(g.metrics.mean_agreement*100).toFixed(0)}%</div><div class="l">متوسط الإجماع</div></div>`;
 document.getElementById("alerts").innerHTML=g.alerts.length?
  g.alerts.map(a=>`<div class="alert a-${a.severity}"><span class="sev">${SV[a.severity]} ${a.severity}</span>
   <div><b>[${a.domain}]</b> ${a.message}<br><small>الإجراء: ${a.action}</small></div></div>`).join("")
  :`<div class="alert a-LOW"><span class="sev">🟢 LOW</span> لا تنبيهات — المنظومة سليمة.</div>`;
 document.getElementById("exec").textContent=g.summary;
}
document.getElementById("run").onclick=()=>{load();
 document.getElementById("live").textContent="تم تشغيل دورة فحص جديدة.";};
load();
</script></body></html>"""

if FASTAPI_AVAILABLE:
    app = FastAPI(title="ProtonAI Governance")

    @app.get("/", response_class=HTMLResponse)
    def index():
        return UI

    @app.get("/api/governance")
    def governance():
        rep = ControlTower().run_cycle(SCANNERS, DRIFT,
                                       list(DOSSIERS.values()))
        return asdict(rep)
