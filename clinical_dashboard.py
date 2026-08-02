"""
ProtonAI - Clinical Dashboard
لوحة دعم القرار السريري: تجمع المؤشرات + التوصية + المقارنة بلوحة واحدة
عارض Markdown + HTML ثابت (بدون مكتبات خارجية، يُفتح بالمتصفح)
نموذج بيانات نظيف = "المقبس"؛ الواجهة التفاعلية الحية = "الفيشة" بمرحلة الكمبيوتر
كل قيمة نصية تُهرّب (html.escape) حمايةً من XSS
"""

import html
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

from quality_indicators import QualityIndicators, Status
from decision_model import DecisionModel, Recommendation

logger = logging.getLogger("ProtonAI.ClinicalDashboard")

# لون خلفية الهيدر حسب الحالة الكلية
_OVERALL_COLOR = {
    Status.GREEN: "#1b7a3d", Status.AMBER: "#b8860b",
    Status.RED: "#a31515", Status.UNKNOWN: "#555555",
}
# لون الشريط الجانبي لبطاقة المؤشر
_IND_COLOR = {
    "GREEN": "#1b7a3d", "AMBER": "#b8860b",
    "RED": "#a31515", "UNKNOWN": "#888888",
}


def _esc(value: Any) -> str:
    """تهريب آمن لأي قيمة نصية (HTML)"""
    return html.escape(str(value), quote=True)


def _fmt_value(value: Any) -> str:
    """تنسيق قيمة للعرض (float → منزلتين، None → —)"""
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


class ClinicalDashboard:
    """
    لوحة سريرية.
    - build: يجمع plan/evaluation/decision/comparison بنموذج لوحة واحد (dict).
    - build_plan: اختصار يقيّم خطة + يوصي + يبني.
    - to_markdown / to_html: عارضان (HTML ثابت يُفتح بالمتصفح).
    - save: يحفظ الصيغتين.
    """

    def __init__(self, quality: Optional[QualityIndicators] = None):
        self.qi = quality if quality is not None else QualityIndicators()

    def build(
        self,
        plan: Any = None,
        evaluation: Optional[Dict[str, Any]] = None,
        decision: Any = None,
        comparison: Optional[Dict[str, Any]] = None,
        title: str = "ProtonAI Clinical Dashboard",
        physician_signed: bool = False,
        physics_signed: bool = False,
    ) -> Dict[str, Any]:
        """بناء نموذج اللوحة (evaluation/decision يُبنيان تلقائياً إن غابا)"""
        if evaluation is None:
            evaluation = (self.qi.evaluate_plan(plan) if plan is not None
                          else self.qi.evaluate({}))
        if decision is None:
            decision = DecisionModel(self.qi).recommend(
                evaluation, physician_signed, physics_signed)
        indicators = [ind.to_dict() for ind in evaluation["indicators"]]
        plan_summary = plan.summary() if plan is not None else {}
        decision_view = {
            "recommendation": decision.recommendation.value,
            "recommendation_reason": decision.recommendation_reason,
            "can_deliver": decision.can_deliver,
            "delivery_blockers": list(decision.delivery_blockers),
            "override": decision.override,
            "specialist_decision": decision.specialist_decision,
            "specialist_id": decision.specialist_id,
        }
        return {
            "title": title,
            "generated_at": datetime.now().isoformat(),
            "plan_summary": plan_summary,
            "indicators": indicators,
            "overall_symbol": evaluation["overall_symbol"],
            "overall_status": evaluation["overall"].name,
            "n_red": evaluation["n_red"], "n_amber": evaluation["n_amber"],
            "n_unknown": evaluation["n_unknown"],
            "decision": decision_view,
            "comparison": comparison,
        }

    def build_plan(
        self, plan: Any, physician_signed: bool = False,
        physics_signed: bool = False, comparison: Optional[Dict[str, Any]] = None,
        title: str = "ProtonAI Clinical Dashboard",
    ) -> Dict[str, Any]:
        """اختصار: يقيّم خطة + يوصي + يبني اللوحة"""
        return self.build(plan=plan, physician_signed=physician_signed,
                          physics_signed=physics_signed, comparison=comparison, title=title)

    # ---------------- Markdown ----------------

    def _md_indicators(self, indicators) -> str:
        """جدول مؤشرات Markdown"""
        lines = ["| الحالة | المؤشر | القيمة | الرسالة |",
                 "|:------:|--------|:------:|---------|"]
        for ind in indicators:
            lines.append(f"| {ind['symbol']} | {_esc(ind['label'])} | "
                         f"{_esc(_fmt_value(ind['value']))} | {_esc(ind['message'])} |")
        return "\n".join(lines)

    def _md_decision(self, dec) -> str:
        """قسم القرار Markdown"""
        out = [f"- **التوصية:** {dec['recommendation']}",
               f"- **السبب:** {dec['recommendation_reason']}",
               f"- **قابل للتسليم الآلي:** {'نعم' if dec['can_deliver'] else 'لا'}"]
        if dec["delivery_blockers"]:
            out.append(f"- **موانع التسليم:** {', '.join(dec['delivery_blockers'])}")
        if dec["specialist_decision"]:
            out.append(f"- **قرار المتخصص:** {dec['specialist_decision']} "
                       f"({dec['specialist_id'] or '—'})")
        if dec["override"]:
            out.append("- ⚠️ **تجاوز موثّق:** المتخصص اعتمد رغم إغلاق البوابة")
        return "\n".join(out)

    def _md_comparison(self, comp) -> str:
        """قسم المقارنة Markdown (اختياري)"""
        out = [f"- **الترتيب:** {' ← '.join(comp['ranking'])}",
               f"- **المفضّلة:** {comp.get('recommended') or 'لا يوجد (تعادل/بلا بيانات)'}",
               f"- **السبب:** {comp['recommendation_reason']}"]
        return "\n".join(out)

    def to_markdown(self, model: Dict[str, Any]) -> str:
        """تصدير اللوحة كنص Markdown"""
        lines = [f"# {model['overall_symbol']} {_esc(model['title'])}", "",
                 f"**الحالة الكلية:** {model['overall_symbol']} {model['overall_status']}  ",
                 f"🔴 {model['n_red']} · 🟡 {model['n_amber']} · ❓ {model['n_unknown']}  ",
                 f"**أُنشئ:** {model['generated_at']}", "", "---", "",
                 "## مؤشرات الجودة", "", self._md_indicators(model["indicators"]), "",
                 "## القرار السريري", "", self._md_decision(model["decision"]), ""]
        if model.get("plan_summary"):
            ps = model["plan_summary"]
            lines += ["## ملخص الخطة", "",
                      f"- **المعرّف:** {_esc(ps.get('plan_id'))}",
                      f"- **المريض (مخفي):** {_esc(ps.get('patient_id'))}",
                      f"- **الاكتمال:** {ps.get('completeness', 0):.0%}", ""]
        if model.get("comparison"):
            lines += ["## مقارنة الخطط", "", self._md_comparison(model["comparison"]), ""]
        return "\n".join(lines)

    # ---------------- HTML ----------------

    def _html_card(self, ind) -> str:
        """بطاقة مؤشر HTML واحدة"""
        color = _IND_COLOR.get(ind["status"], "#888")
        return (f'<div class="card" style="border-left:6px solid {color}">'
                f'<div class="sym">{ind["symbol"]}</div>'
                f'<div class="lbl">{_esc(ind["label"])}</div>'
                f'<div class="val">{_esc(_fmt_value(ind["value"]))}</div>'
                f'<div class="msg">{_esc(ind["message"])}</div></div>')

    def to_html(self, model: Dict[str, Any]) -> str:
        """تصدير اللوحة كصفحة HTML ثابتة (تُفتح بالمتصفح، بدون مكتبات)"""
        overall = Status[model["overall_status"]]
        hcolor = _OVERALL_COLOR.get(overall, "#555")
        dec = model["decision"]
        cards = "\n".join(self._html_card(i) for i in model["indicators"])
        blockers_html = ("".join(f"<li>{_esc(b)}</li>" for b in dec["delivery_blockers"])
                         if dec["delivery_blockers"] else "<li>لا يوجد</li>")
        override_html = ('<p class="warn">⚠️ تجاوز موثّق: المتخصص اعتمد رغم إغلاق البوابة</p>'
                         if dec["override"] else "")
        comp_html = ""
        if model.get("comparison"):
            c = model["comparison"]
            comp_html = (f'<section><h2>مقارنة الخطط</h2>'
                         f'<p><b>الترتيب:</b> {_esc(" ← ".join(c["ranking"]))}</p>'
                         f'<p><b>المفضّلة:</b> {_esc(c.get("recommended") or "لا يوجد")}</p>'
                         f'<p>{_esc(c["recommendation_reason"])}</p></section>')
        ps = model.get("plan_summary") or {}
        plan_html = (f'<section><h2>ملخص الخطة</h2>'
                     f'<p>المعرّف: {_esc(ps.get("plan_id"))} · '
                     f'المريض (مخفي): {_esc(ps.get("patient_id"))} · '
                     f'الاكتمال: {ps.get("completeness", 0):.0%}</p></section>'
                     if ps else "")
        css = ("body{font-family:system-ui,Arial,sans-serif;margin:0;background:#f4f6f8;"
               "direction:rtl;color:#1a1a1a}"
               "header{background:%s;color:#fff;padding:24px 32px}"
               "header h1{margin:0 0 6px}header .sub{opacity:.92}"
               "main{padding:24px 32px;max-width:960px;margin:auto}"
               "section{background:#fff;border-radius:10px;padding:18px 22px;margin:18px 0;"
               "box-shadow:0 1px 4px rgba(0,0,0,.08)}"
               "h2{margin-top:0;font-size:1.1rem;border-bottom:2px solid #eee;padding-bottom:8px}"
               ".grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:14px}"
               ".card{background:#fff;border-radius:8px;padding:14px;box-shadow:0 1px 3px rgba(0,0,0,.08)}"
               ".sym{font-size:1.8rem}.lbl{font-weight:600;margin:4px 0}.val{color:#555}"
               ".msg{font-size:.85rem;color:#444;margin-top:6px}"
               ".decision{border-right:6px solid %s}"
               ".warn{background:#fff3cd;color:#664d03;padding:8px 12px;border-radius:6px}"
               "ul{margin:6px 0;padding-right:20px}") % (hcolor, hcolor)
        return (f'<!DOCTYPE html><html lang="ar" dir="rtl"><head>'
                f'<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
                f'<title>{_esc(model["title"])}</title><style>{css}</style></head><body>'
                f'<header><h1>{model["overall_symbol"]} {_esc(model["title"])}</h1>'
                f'<div class="sub">الحالة الكلية: {model["overall_symbol"]} {model["overall_status"]} · '
                f'🔴 {model["n_red"]} · 🟡 {model["n_amber"]} · ❓ {model["n_unknown"]} · '
                f'{_esc(model["generated_at"])}</div></header><main>'
                f'<section><h2>مؤشرات الجودة</h2><div class="grid">{cards}</div></section>'
                f'<section class="decision"><h2>القرار السريري</h2>'
                f'<p><b>التوصية:</b> {_esc(dec["recommendation"])}</p>'
                f'<p>{_esc(dec["recommendation_reason"])}</p>'
                f'<p><b>قابل للتسليم الآلي:</b> {"نعم" if dec["can_deliver"] else "لا"}</p>'
                f'<p><b>موانع التسليم:</b></p><ul>{blockers_html}</ul>'
                f'{("<p><b>قرار المتخصص:</b> "+_esc(dec["specialist_decision"])+" ("+_esc(dec["specialist_id"] or "—")+")</p>") if dec["specialist_decision"] else ""}'
                f'{override_html}</section>{plan_html}{comp_html}</main></body></html>')

    def save(self, model: Dict[str, Any], path_md, path_html=None) -> None:
        """حفظ اللوحة (Markdown + HTML اختياري)"""
        path_md = Path(path_md)
        path_md.parent.mkdir(parents=True, exist_ok=True)
        with open(path_md, "w", encoding="utf-8") as f:
            f.write(self.to_markdown(model))
        if path_html is not None:
            path_html = Path(path_html)
            path_html.parent.mkdir(parents=True, exist_ok=True)
            with open(path_html, "w", encoding="utf-8") as f:
                f.write(self.to_html(model))
        logger.info(f"تم حفظ اللوحة في: {path_md}"
                    + (f" + {path_html}" if path_html else ""))
