"""
ProtonAI - Publication-Ready Documentation
مولّد توثيق جاهز للنشر يقرأ الكود نفسه عبر تحليل ساكن (ast)
يستخرج الوحدات + الكلاسات + الدوال + أول سطر docstring → وثيقة معمارية/API
ساكن = آمن (لا يشغّل كود) + متزامن دايماً مع المصدر (لا يتقادم)
"""

import ast
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger("ProtonAI.PublicationDocs")


def _first_line(doc: Optional[str]) -> str:
    """أول سطر من docstring (أو نص فاضي)"""
    return (doc or "").strip().split("\n")[0]


class DocumentationGenerator:
    """
    مولّد التوثيق.
    - scan: يقرأ كل *.py (يتجاوز test_ و_) ويستخرج البنية.
    - to_markdown: وثيقة معمارية/API جاهزة للنشر.
    - include: تصفية لوحدات معينة (اختياري).
    """

    def __init__(
        self,
        root: Optional[str | Path] = None,
        include: Optional[List[str]] = None,
    ):
        self.root = Path(root) if root is not None else Path(__file__).parent
        self.include = set(include) if include else None

    def _parse_module(self, path: Path) -> Dict[str, Any]:
        """تحليل ساكن لوحدة: كلاسات + دوال علوية + أول سطر docstring"""
        tree = ast.parse(path.read_text(encoding="utf-8"))
        classes: List[Dict[str, str]] = []
        functions: List[Dict[str, str]] = []
        for node in tree.body:  # المستوى العلوي فقط
            if isinstance(node, ast.ClassDef):
                classes.append({"name": node.name,
                                "doc": _first_line(ast.get_docstring(node))})
            elif isinstance(node, ast.FunctionDef):
                functions.append({"name": node.name,
                                  "doc": _first_line(ast.get_docstring(node))})
        return {"module": path.stem, "classes": classes, "functions": functions}

    def scan(self) -> List[Dict[str, Any]]:
        """مسح الوحدات (يتجاوز test_ و _ والملفات غير الصالحة)"""
        out: List[Dict[str, Any]] = []
        for p in sorted(self.root.glob("*.py")):
            if p.name.startswith("test_") or p.name.startswith("_"):
                continue
            if self.include is not None and p.stem not in self.include:
                continue
            try:
                out.append(self._parse_module(p))
            except Exception:
                logger.warning(f"تعذّر تحليل: {p.name}")
        return out

    def to_markdown(self) -> str:
        """وثيقة معمارية/API Markdown جاهزة للنشر"""
        mods = self.scan()
        lines = ["# ProtonAI — توثيق جاهز للنشر (مولّد آلياً من الكود)", "",
                 f"**عدد الوحدات:** {len(mods)}", "", "## خريطة الوحدات", ""]
        if not mods:
            lines.append("_لا توجد وحدات._")
        for m in mods:
            lines.append(f"### `{m['module']}`")
            for c in m["classes"]:
                suffix = f" — {c['doc']}" if c["doc"] else ""
                lines.append(f"- class `{c['name']}`{suffix}")
            for f in m["functions"]:
                suffix = f" — {f['doc']}" if f["doc"] else ""
                lines.append(f"- def `{f['name']}`{suffix}")
            lines.append("")
        return "\n".join(lines)
