"""
ProtonAI - Release Versioning
إصدار مُرقّم دلالياً + سجل تغييرات تلقائي + checklist إطلاق مؤسسي
الترقية تلقائية ومنطقية: breaking→major، feature→minor، fix/docs→patch
الإصدار مسجّل بتاريخه وحالة checklistه — تاريخ إطلاق قابل للتدقيق
"""

import logging
from datetime import datetime
from typing import Dict, Any, List

logger = logging.getLogger("ProtonAI.ReleaseVersioning")

_KINDS = ("breaking", "feature", "fix", "docs")
_KIND_LABELS = {"breaking": "تغييرات كاسرة", "feature": "ميزات",
                "fix": "إصلاحات", "docs": "توثيق"}
_KIND_ORDER = {"breaking": 0, "feature": 1, "fix": 2, "docs": 3}

# بنود checklist الإطلاق المؤسسي (كلها لازم خضرا)
DEFAULT_CHECKLIST = (
    "tests_green", "coverage_ok", "audit_enabled", "rbac_enforced",
    "docs_generated", "reproducibility_packaged", "external_validated",
)


class SemanticVersion:
    """نسخة دلالية major.minor.patch"""

    def __init__(self, major: int = 0, minor: int = 0, patch: int = 0):
        for v in (major, minor, patch):
            if not isinstance(v, int) or v < 0:
                raise ValueError("مكوّنات النسخة أعداد صحيحة >= 0")
        self.major, self.minor, self.patch = major, minor, patch

    @classmethod
    def parse(cls, s: str) -> "SemanticVersion":
        parts = str(s).strip().split(".")
        if len(parts) != 3:
            raise ValueError(f"نسخة غير صالحة: {s} (يلزم major.minor.patch)")
        return cls(int(parts[0]), int(parts[1]), int(parts[2]))

    def bump_major(self) -> "SemanticVersion":
        return SemanticVersion(self.major + 1, 0, 0)

    def bump_minor(self) -> "SemanticVersion":
        return SemanticVersion(self.major, self.minor + 1, 0)

    def bump_patch(self) -> "SemanticVersion":
        return SemanticVersion(self.major, self.minor, self.patch + 1)

    def _tuple(self):
        return (self.major, self.minor, self.patch)

    def __eq__(self, other):
        return self._tuple() == other._tuple()

    def __lt__(self, other):
        return self._tuple() < other._tuple()

    def __str__(self):
        return f"{self.major}.{self.minor}.{self.patch}"


class ReleaseManager:
    """
    مدير إصدارات.
    - add_change: يجمع تغييراً بنوعه.
    - changelog: سجل Markdown مجمّع بالنوع.
    - release: يرقّي النسخة (حسب أخطر تغيير) ويصدر سجلاً موثقاً.
    - set_check / ready_to_launch: checklist الإطلاق المؤسسي.
    """

    def __init__(self, version: str = "0.1.0"):
        self.version = SemanticVersion.parse(version)
        self.pending: List[Dict[str, str]] = []
        self.releases: List[Dict[str, Any]] = []
        self.checklist: Dict[str, bool] = {k: False for k in DEFAULT_CHECKLIST}

    def add_change(self, text: str, kind: str = "feature") -> None:
        """تسجيل تغيير قيد الإصدار"""
        if kind not in _KINDS:
            raise ValueError(f"نوع غير صالح: {kind}. المسموح: {_KINDS}")
        self.pending.append({"kind": kind, "text": str(text)})

    def _top_kind(self) -> str:
        """أخطر نوع بين التغييرات المعلّقة"""
        return min(self.pending, key=lambda c: _KIND_ORDER[c["kind"]])["kind"]

    def changelog(self) -> str:
        """سجل تغييرات Markdown مجمّع بالنوع"""
        lines = ["## سجل التغييرات (Changelog)", ""]
        if not self.pending:
            lines.append("_لا تغييرات معلّقة._")
        for kind in sorted(self.pending and _KINDS or _KINDS,
                           key=lambda k: _KIND_ORDER[k]):
            items = [c for c in self.pending if c["kind"] == kind]
            if items:
                lines.append(f"### {_KIND_LABELS[kind]}")
                lines += [f"- {c['text']}" for c in items]
                lines.append("")
        return "\n".join(lines)

    def set_check(self, item: str, ok: bool) -> None:
        """تحديث بند checklist"""
        if item not in self.checklist:
            raise ValueError(f"بند غير معروف: {item}")
        self.checklist[item] = bool(ok)

    def ready_to_launch(self) -> bool:
        """هل كل بنود checklist خضرا؟"""
        return all(self.checklist.values())

    def release(self) -> Dict[str, Any]:
        """إصدار نسخة: ترقية حسب أخطر تغيير + سجل موثق"""
        if not self.pending:
            raise ValueError("لا تغييرات معلّقة للإصدار")
        kind = self._top_kind()
        if kind == "breaking":
            self.version = self.version.bump_major()
        elif kind == "feature":
            self.version = self.version.bump_minor()
        else:
            self.version = self.version.bump_patch()
        record = {
            "version": str(self.version),
            "bump": kind,
            "changes": list(self.pending),
            "changelog": self.changelog(),
            "checklist": dict(self.checklist),
            "ready_to_launch": self.ready_to_launch(),
            "timestamp": datetime.now().isoformat(),
        }
        self.releases.append(record)
        self.pending = []
        logger.info(f"release v{record['version']} ({kind})")
        return record
