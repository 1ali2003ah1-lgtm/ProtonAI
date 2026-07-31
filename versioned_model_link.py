"""
ProtonAI - Versioned Model Link
سلسلة الإثبات الكاملة: ربط النموذج المسجّل بالتجربة القابلة للتكرار
يتحقق من تطابق بصمات (النموذج ← التجربة ← البيانات ← التقسيم) ويكشف أي تعارض
"""

import logging
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

from experiment_tracker import fingerprint

logger = logging.getLogger("ProtonAI.VersionedModelLink")


@dataclass
class CheckResult:
    """فحص تطابق واحد"""
    name: str
    passed: bool
    expected: Any = None
    got: Any = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LinkRecord:
    """سجل ربط نموذج بتجربة مع حالة التحقق"""
    model_id: str
    name: str
    version: int
    data_fingerprint: str
    split_fingerprint: str
    experiment_id: str
    metrics: Dict[str, Any] = field(default_factory=dict)
    verified: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class VersionedModelLink:
    """
    طبقة الربط والتحقق فوق registry + tracker.
    - link: يربط نموذج بتجربة ويملأ البصمات (ويكشف التعارض).
    - verify: يتحقق من تطابق البصمات المدخلة مع المحفوظة.
    - lineage: سلسلة النسب الكاملة لنموذج.
    - find_by_experiment / find_by_data: استعلامات.
    """

    def __init__(self, registry: Any, tracker: Any = None):
        self.registry = registry
        self.tracker = tracker

    def _entry(self, model_id: str):
        """استرجاع entry (يرمي ValueError لو مو موجود، عبر registry)"""
        return self.registry.get(model_id)

    def _get_experiment(self, experiment_id: str):
        """استرجاع تجربة من الـ tracker بالـ id (None لو ما لقاها)"""
        if self.tracker is None or not experiment_id:
            return None
        for e in self.tracker.experiments:
            if e.experiment_id == experiment_id:
                return e
        return None

    def link(
        self,
        model_id: str,
        experiment_id: str = "",
        data: Any = None,
    ) -> LinkRecord:
        """
        ربط نموذج بتجربة + ملء البصمات + كشف التعارض.
        verified=True فقط لو كل البصمات متسقة.
        """
        entry = self._entry(model_id)
        verified = True

        # ربط التجربة
        if experiment_id:
            entry.experiment_id = experiment_id
        exp = self._get_experiment(entry.experiment_id)

        # بصمة البيانات: من data المدخل، أو من التجربة لو فاضي
        if data is not None:
            fp = fingerprint(data)
            if entry.data_fingerprint and entry.data_fingerprint != fp:
                logger.warning(f"تعارض بصمة بيانات بالنموذج {model_id}: "
                               f"محفوظ={entry.data_fingerprint[:8]} ≠ مدخل={fp[:8]}")
                verified = False
            else:
                entry.data_fingerprint = fp
        elif not entry.data_fingerprint and exp is not None:
            entry.data_fingerprint = exp.data_fingerprint

        # اتساق النموذج ↔ التجربة
        if exp is not None and entry.data_fingerprint:
            if exp.data_fingerprint != entry.data_fingerprint:
                logger.warning(f"تعارض نموذج↔تجربة بـ {model_id}: "
                               f"entry={entry.data_fingerprint[:8]} ≠ exp={exp.data_fingerprint[:8]}")
                verified = False

        split_fp = exp.split_fingerprint if exp is not None else ""
        logger.info(f"ربط {model_id} ← تجربة={entry.experiment_id or '—'} "
                    f"(verified={verified})")
        return LinkRecord(
            model_id=model_id, name=entry.name, version=entry.version,
            data_fingerprint=entry.data_fingerprint, split_fingerprint=split_fp,
            experiment_id=entry.experiment_id, metrics=dict(entry.metrics),
            verified=verified,
        )

    def verify(
        self,
        model_id: str,
        data: Any = None,
        split_fp: str = "",
        experiment_id: str = "",
    ) -> Dict[str, Any]:
        """
        التحقق من تطابق البصمات المدخلة مع المحفوظة.
        يرجع {valid, checks:[...]} — valid=True فقط لو كل الفحوص نجحت.
        """
        entry = self._entry(model_id)
        checks: List[CheckResult] = []

        if data is not None:
            fp = fingerprint(data)
            checks.append(CheckResult(
                "data_fingerprint", fp == entry.data_fingerprint,
                expected=entry.data_fingerprint, got=fp))

        if experiment_id:
            checks.append(CheckResult(
                "experiment_id", experiment_id == entry.experiment_id,
                expected=entry.experiment_id, got=experiment_id))

        exp = self._get_experiment(entry.experiment_id)
        if split_fp:
            got_split = exp.split_fingerprint if exp is not None else ""
            checks.append(CheckResult(
                "split_fingerprint", split_fp == got_split,
                expected=got_split, got=split_fp))

        # اتساق النموذج ↔ التجربة (فحص داخلي دايماً لو التجربة موجودة)
        if exp is not None and entry.data_fingerprint:
            checks.append(CheckResult(
                "model_experiment_consistency",
                exp.data_fingerprint == entry.data_fingerprint,
                expected=entry.data_fingerprint, got=exp.data_fingerprint))

        valid = all(c.passed for c in checks) if checks else True
        return {"valid": valid, "model_id": model_id,
                "checks": [c.to_dict() for c in checks]}

    def lineage(self, model_id: str) -> Dict[str, Any]:
        """سلسلة النسب الكاملة لنموذج (model → experiment → data → split → metrics)"""
        entry = self._entry(model_id)
        exp = self._get_experiment(entry.experiment_id)
        chain: Dict[str, Any] = {
            "model": {
                "model_id": entry.model_id, "name": entry.name,
                "version": entry.version, "status": entry.status.value,
                "metrics": dict(entry.metrics),
                "registered_at": entry.registered_at,
            },
            "data_fingerprint": entry.data_fingerprint,
            "experiment_id": entry.experiment_id,
        }
        if exp is not None:
            chain["experiment"] = {
                "experiment_id": exp.experiment_id, "name": exp.name,
                "config": dict(exp.config), "seed": exp.seed,
                "split_fingerprint": exp.split_fingerprint,
                "data_fingerprint": exp.data_fingerprint,
                "metrics": dict(exp.metrics),
            }
        return chain

    def find_by_experiment(self, experiment_id: str) -> List[Any]:
        """كل النماذج المنبثقة من تجربة معيّنة"""
        return [e for e in self.registry.list_all()
                if e.experiment_id == experiment_id]

    def find_by_data(self, data: Any) -> List[Any]:
        """كل النماذج المدرّبة على نفس البيانات"""
        fp = fingerprint(data)
        return [e for e in self.registry.list_all() if e.data_fingerprint == fp]
