"""H2 FINAL: landing page (Pages) + release notes generator."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "docs" / "site" / "index.html"
NOTES = ROOT / "docs" / "publication" / "RELEASE-NOTES-v0.9.0.md"
SUM = ROOT / "docs" / "publication" / "publication_summary.json"

HTML = """<!doctype html><html><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<meta property="og:title" content="ProtonAI"/>
<meta property="og:description" content="Open, auditable AI contouring for proton therapy with live dose-impact."/>
<meta property="og:type" content="website"/>
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>&#9889;</text></svg>"/>
<title>ProtonAI — Auditable AI for Proton Therapy</title>
<style>:root{--bg:#070b14;--card:rgba(22,27,39,.75);--line:#2a3242;--a:#22d3ee}
*{box-sizing:border-box}body{margin:0;font-family:system-ui;color:#e6edf3;background:var(--bg)}
.wrap{max-width:960px;margin:0 auto;padding:48px 24px}
h1{font-size:44px;background:linear-gradient(90deg,var(--a),#a78bfa);-webkit-background-clip:text;color:transparent}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:20px;margin:14px 0}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
.big{font-size:30px;font-weight:800;color:var(--a)}
.badge{display:inline-block;margin:2px;padding:4px 10px;border-radius:999px;background:#1b2334;border:1px solid var(--line);font-size:12px}
button{background:#1b2334;color:#e6edf3;border:1px solid var(--line);border-radius:8px;padding:8px 14px;float:right}
footer{opacity:.6;margin-top:30px;font-size:13px}</style></head><body><div class="wrap">
<button onclick="toggle()">ع / EN</button><h1>ProtonAI</h1>
<p data-en="Open, auditable AI contouring assistance for proton therapy — live dose-impact." data-ar="منصة مفتوحة وقابلة للتدقيق لتجزئة العلاج بالبروتون — أثر جرعة حي.">…</p>
<div><span class="badge">DOI: __DOI__</span><span class="badge">v0.9.0</span></div>
<div class="grid">
<div class="card"><div class="big">__D95__</div><span data-en="D95 improvement" data-ar="تحسن D95">…</span></div>
<div class="card"><div class="big">__P__</div><span>p (Wilcoxon)</span></div>
<div class="card"><div class="big">__VERDICT__</div><span data-en="Verdict" data-ar="الحكم">…</span></div></div>
<div class="card">dTCP +__TCP__ · dNTCP __NTCP__</div>
<div class="card"><b>Cite</b>: [Authors]. ProtonAI v0.9.0. Zenodo. DOI: __DOI__.</div>
<div class="card" data-en="Status: synthetic validation complete; NOT for clinical use." data-ar="الحالة: التحقق الاصطناعي مكتمل؛ ليس للاستخدام السريري.">…</div>
<footer>github.com/1ali2003ah1-lgtm/ProtonAI · MIT</footer></div>
<script>let lang="en";function apply(){document.querySelectorAll("[data-en]").forEach(e=>{e.textContent=lang==="en"?e.dataset.en:e.dataset.ar;});document.documentElement.dir=lang==="ar"?"rtl":"ltr";}function toggle(){lang=lang==="en"?"ar":"en";apply();}apply();</script></body></html>"""


def main():
    n = json.loads(SUM.read_text(encoding="utf-8")) if SUM.exists() else {}
    html = (HTML.replace("__D95__", f"{n.get('d95_mean',0):.3f}")
            .replace("__P__", f"{n.get('p',1):.4f}")
            .replace("__VERDICT__", str(n.get("verdict","pending")))
            .replace("__TCP__", f"{n.get('tcp',0):.3f}")
            .replace("__NTCP__", f"{n.get('ntcp',0):.4f}")
            .replace("__DOI__", "10.5281/zenodo.pending"))
    SITE.parent.mkdir(parents=True, exist_ok=True)
    SITE.write_text(html, encoding="utf-8")
    ntests = len(list(ROOT.glob("test_*.py")))
    NOTES.write_text(f"""# RELEASE NOTES v0.9.0\n\nGuarded test modules: {ntests}.\nKey result: D95 {n.get('d95_mean',0):.3f} (p={n.get('p',1):.4f}), {n.get('verdict','pending')}.\nNOT for clinical use; real-patient validation pending.\n""", encoding="utf-8")
    print(f"H2 FINAL: site + release notes ({ntests} test modules)")


if __name__ == "__main__":
    main()
