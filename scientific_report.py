"""
ProtonAI - Scientific Report
بناء تقارير علمية منسّقة (Markdown + JSON) من نتائج المقيّم العلمي
كل رقم يطلع معه فاصل ثقة 95% بصيغة جاهزة للأوراق البحثية
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger("ProtonAI.ScientificReport")


def _fmt(x: Any, digits: int = 4) -> str:
    """تنسيق رقم لأرقام عشرية ثابتة، أو نص كما هو"""
    if isinstance(x, float):
        return f"{x:.{digits}f}"
    return str(x)


def format_ci(mean: float, ci_low: float, ci_high: float, digits: int = 4) -> str:
    """تنسيق قيمة مع فاصل ثقة: 0.9000 [0.8500–0.9500]"""
    return f"{_fmt(mean, digits)} [{_fmt(ci_low, digits)}–{_fmt(ci_high, digits)}]"


class ScientificReport:
    """
    تقرير علمي قابل للبناء قطعة قطعة.
    - add_metrics / add_cross_validation / add_comparison: إضافة أقسام.
    - to_markdown / to_dict: تصدير بصيغتين.
    - save_markdown / save_json: حفظ على القرص.
    """

    def __init__(
        self,
        title: str = "ProtonAI Scientific Report",
        author: str = "",
        dataset_name: str = "",
    ):
        self.title = title
        self.author = author
        self.dataset_name = dataset_name
        self.sections: List[Dict[str, Any]] = []
        self.metadata: Dict[str, Any] = {"generated_at": datetime.now().isoformat()}

    def add_section(self, name: str, content: Dict[str, Any]) -> None:
        """إضافة قسم عام للتقرير"""
        self.sections.append({"name": name, "content": content})

    def add_metrics(self, metrics: Dict[str, Any], name: str = "Evaluation Metrics") -> None:
        """إضافة قسم مقاييس تقييم"""
        self.add_section(name, {"type": "metrics", "data": metrics})

    def add_cross_validation(self, cv_result: Dict[str, Any], name: str = "Cross-Validation") -> None:
        """إضافة قسم cross-validation مع فواصل الثقة"""
        self.add_section(name, {"type": "cv", "data": cv_result})

    def add_comparison(self, comp_result: Dict[str, Any], name: str = "Model Comparison") -> None:
        """إضافة قسم مقارنة نماذج مع الترتيب"""
        self.add_section(name, {"type": "comparison", "data": comp_result})

    def to_dict(self) -> Dict[str, Any]:
        """تصدير التقرير كقاموس (للـ JSON)"""
        return {
            "title": self.title,
            "author": self.author,
            "dataset_name": self.dataset_name,
            "metadata": self.metadata,
            "sections": self.sections,
        }

    def _render_metrics_table(
        self, mean_metrics: Dict[str, float], ci_metrics: Optional[Dict[str, Any]] = None
    ) -> str:
        """جدول markdown: المقياس | القيمة | فاصل الثقة"""
        ci_metrics = ci_metrics or {}
        lines = ["| Metric | Value | 95% CI |", "|--------|-------|--------|"]
        for key in sorted(mean_metrics.keys()):
            val = _fmt(mean_metrics[key])
            if key in ci_metrics:
                ci = f"[{_fmt(ci_metrics[key]['ci_low'])}–{_fmt(ci_metrics[key]['ci_high'])}]"
            else:
                ci = "—"
            lines.append(f"| {key} | {val} | {ci} |")
        return "\n".join(lines)

    def _render_cv(self, data: Dict[str, Any]) -> str:
        """عرض قسم cross-validation"""
        out = [
            f"- **Task:** {data.get('task')}",
            f"- **Folds (k):** {data.get('k')}",
            f"- **Samples:** {data.get('n')}",
            f"- **Stratified:** {data.get('stratified')}",
            "",
            "### Mean Metrics with 95% CI",
            "",
            self._render_metrics_table(data.get("mean_metrics", {}), data.get("ci_metrics", {})),
        ]
        return "\n".join(out)

    def _render_comparison(self, data: Dict[str, Any]) -> str:
        """عرض قسم مقارنة النماذج مع الترتيب"""
        better = "higher is better" if data.get("higher_better") else "lower is better"
        out = [f"- **Primary metric:** {data.get('primary_metric')} ({better})", "", "### Ranking", ""]
        for i, name in enumerate(data.get("ranking", []), 1):
            res = data["results"][name]
            pm = data["primary_metric"]
            val = res["mean_metrics"].get(pm)
            ci = res.get("ci_metrics", {}).get(pm)
            val_str = format_ci(val, ci["ci_low"], ci["ci_high"]) if ci else _fmt(val)
            out.append(f"{i}. **{name}** — {pm} = {val_str}")
        return "\n".join(out)

    def _render_metrics(self, data: Dict[str, Any]) -> str:
        """عرض قسم مقاييس مباشرة"""
        if isinstance(data, dict) and "task" in data:
            out = [f"- **Task:** {data.get('task')}", f"- **Samples:** {data.get('samples')}", "",
                   "| Metric | Value |", "|--------|-------|"]
            for k, v in data.items():
                if k in ("task", "samples", "classes", "confusion"):
                    continue
                if isinstance(v, float):
                    out.append(f"| {k} | {_fmt(v)} |")
            return "\n".join(out)
        return "```json\n" + json.dumps(data, indent=2, ensure_ascii=False, default=str) + "\n```"

    def _render_section(self, sec: Dict[str, Any]) -> str:
        """اختيار العارض المناسب لنوع القسم"""
        t = sec["content"].get("type")
        data = sec["content"].get("data", {})
        if t == "cv":
            return self._render_cv(data)
        if t == "comparison":
            return self._render_comparison(data)
        if t == "metrics":
            return self._render_metrics(data)
        return "```json\n" + json.dumps(data, indent=2, ensure_ascii=False, default=str) + "\n```"

    def to_markdown(self) -> str:
        """تصدير التقرير كنص Markdown منسّق"""
        lines = [f"# {self.title}", ""]
        if self.author:
            lines.append(f"**Author:** {self.author}")
        if self.dataset_name:
            lines.append(f"**Dataset:** {self.dataset_name}")
        lines.append(f"**Generated:** {self.metadata['generated_at']}")
        lines += ["", "---", ""]
        for sec in self.sections:
            lines.append(f"## {sec['name']}")
            lines.append("")
            lines.append(self._render_section(sec))
            lines.append("")
        return "\n".join(lines)

    def save_markdown(self, path: str | Path) -> None:
        """حفظ التقرير كملف Markdown"""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.to_markdown())
        logger.info(f"تم حفظ التقرير العلمي (markdown) في: {path}")

    def save_json(self, path: str | Path) -> None:
        """حفظ التقرير كملف JSON"""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False, default=str)
        logger.info(f"تم حفظ التقرير العلمي (json) في: {path}")
