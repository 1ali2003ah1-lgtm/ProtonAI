"""
ProtonAI - Model Registry
مكتبة النماذج المؤرشفة: نسخ متصاعدة + بصمات + مقاييس + promote/archive
كل نموذج يُحفظ بملف مستقل مع metadata قابل للاسترجاع (MLOps-style)
"""

import json
import pickle
import logging
import hashlib
import uuid
import re
from enum import Enum
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

logger = logging.getLogger("ProtonAI.ModelRegistry")


class ModelStatus(str, Enum):
    """حالة النسخة المسجّلة"""
    ACTIVE = "active"          # نشطة ومتاحة
    PRODUCTION = "production"  # النسخة المعتمدة للاستخدام
    ARCHIVED = "archived"      # متقاعدة (محفوظة لكن غير مفضّلة)


def _safe_name(name: str) -> str:
    """توحيد الاسم لاستخدامه كاسم ملف آمن"""
    return re.sub(r"[^a-zA-Z0-9_-]", "_", str(name).strip()) or "model"


@dataclass
class ModelEntry:
    """سجل نسخة نموذج واحدة"""
    model_id: str
    name: str
    version: int
    model_path: str
    metrics: Dict[str, Any] = field(default_factory=dict)
    data_fingerprint: str = ""
    experiment_id: str = ""
    tags: List[str] = field(default_factory=list)
    notes: str = ""
    status: ModelStatus = ModelStatus.ACTIVE
    registered_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ModelEntry":
        return cls(
            model_id=d["model_id"], name=d["name"], version=d["version"],
            model_path=d["model_path"], metrics=d.get("metrics", {}),
            data_fingerprint=d.get("data_fingerprint", ""),
            experiment_id=d.get("experiment_id", ""),
            tags=d.get("tags", []), notes=d.get("notes", ""),
            status=ModelStatus(d.get("status", "active")),
            registered_at=d.get("registered_at", ""),
        )


class ModelRegistry:
    """
    مكتبة النماذج.
    - register: يحفظ النموذج بملف + يسجّل metadata بنسخة متصاعدة.
    - get / get_by_version / load_model: استرجاع.
    - promote: يعلّم نسخة كـ production (واحدة لكل اسم).
    - archive: يؤرشف نسخة.
    - best: أفضل نسخة نشطة/معتمدة حسب مقياس.
    - save / load: حفظ سجل الـ metadata.
    """

    def __init__(self, store_dir: str | Path, audit: Any = None):
        self.store_dir = Path(store_dir)
        self.models_dir = self.store_dir / "models"
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.audit = audit
        self.entries: List[ModelEntry] = []

    def _next_version(self, name: str) -> int:
        """رقم النسخة التالي لاسم معيّن"""
        versions = [e.version for e in self.entries if e.name == name]
        return (max(versions) + 1) if versions else 1

    def register(
        self,
        name: str,
        model: Any,
        metrics: Optional[Dict[str, Any]] = None,
        data_fingerprint: str = "",
        experiment_id: str = "",
        tags: Optional[List[str]] = None,
        notes: str = "",
    ) -> ModelEntry:
        """تسجيل نسخة نموذج جديدة (يحفظ النموذج فعلياً)"""
        # رفض نموذج غير مدرّب إن أعلن عن حالته
        if hasattr(model, "is_trained") and not model.is_trained:
            raise RuntimeError("لا يمكن تسجيل نموذج غير مدرّب")
        model_id = hashlib.sha256(
            (name + datetime.now().isoformat() + uuid.uuid4().hex).encode()
        ).hexdigest()[:12]
        version = self._next_version(name)
        filename = f"{_safe_name(name)}_{model_id}.pkl"
        with open(self.models_dir / filename, "wb") as f:
            pickle.dump(model, f)
        entry = ModelEntry(
            model_id=model_id, name=name, version=version,
            model_path=filename, metrics=dict(metrics or {}),
            data_fingerprint=data_fingerprint, experiment_id=experiment_id,
            tags=list(tags or []), notes=notes,
        )
        self.entries.append(entry)
        logger.info(f"تم تسجيل {name} v{version} ({model_id})")
        if self.audit is not None:
            self.audit.log("model_registry", "register", name,
                           _audit_outcome(self.audit, "SUCCESS"),
                           {"model_id": model_id, "version": version})
        return entry

    def _find(self, model_id: str) -> ModelEntry:
        for e in self.entries:
            if e.model_id == model_id:
                return e
        raise ValueError(f"نموذج غير موجود: {model_id}")

    def get(self, model_id: str) -> ModelEntry:
        """استرجاع metadata نسخة بالـ id"""
        return self._find(model_id)

    def get_by_version(self, name: str, version: int) -> ModelEntry:
        """استرجاع metadata نسخة بالاسم ورقم النسخة"""
        for e in self.entries:
            if e.name == name and e.version == version:
                return e
        raise ValueError(f"نسخة غير موجودة: {name} v{version}")

    def load_model(self, model_id: str) -> Any:
        """تحميل النموذج الفعلي من القرص"""
        entry = self._find(model_id)
        path = self.models_dir / entry.model_path
        if not path.exists():
            raise FileNotFoundError(f"ملف النموذج مفقود: {path}")
        with open(path, "rb") as f:
            return pickle.load(f)

    def list_all(self) -> List[ModelEntry]:
        """كل النسخ المسجّلة"""
        return list(self.entries)

    def list_by_name(self, name: str) -> List[ModelEntry]:
        """نسخ اسم معيّن"""
        return [e for e in self.entries if e.name == name]

    def list_by_status(self, status: ModelStatus) -> List[ModelEntry]:
        """نسخ بحالة معيّنة"""
        return [e for e in self.entries if e.status == status]

    def promote(self, model_id: str) -> ModelEntry:
        """تعليم نسخة كـ production (ينزّل production القديم لنفس الاسم)"""
        entry = self._find(model_id)
        if entry.status == ModelStatus.ARCHIVED:
            raise ValueError("لا يمكن ترقية نسخة مؤرشفة")
        # تنزيل أي production سابق لنفس الاسم
        for e in self.entries:
            if e.name == entry.name and e.status == ModelStatus.PRODUCTION:
                e.status = ModelStatus.ACTIVE
        entry.status = ModelStatus.PRODUCTION
        logger.info(f"تمت ترقية {entry.name} v{entry.version} إلى production")
        if self.audit is not None:
            self.audit.log("model_registry", "promote", entry.name,
                           _audit_outcome(self.audit, "SUCCESS"),
                           {"model_id": model_id, "version": entry.version})
        return entry

    def archive(self, model_id: str) -> ModelEntry:
        """أرشفة نسخة (تبقى محفوظة لكن غير مفضّلة)"""
        entry = self._find(model_id)
        entry.status = ModelStatus.ARCHIVED
        logger.info(f"تمت أرشفة {entry.name} v{entry.version}")
        return entry

    def best(
        self, name: str, metric: str, higher_better: bool = True
    ) -> Optional[ModelEntry]:
        """أفضل نسخة غير مؤرشفة لاسم معيّن حسب مقياس"""
        candidates = [e for e in self.entries
                      if e.name == name and metric in e.metrics
                      and e.status != ModelStatus.ARCHIVED]
        if not candidates:
            return None
        return (max(candidates, key=lambda e: e.metrics[metric]) if higher_better
                else min(candidates, key=lambda e: e.metrics[metric]))

    def save(self, path: Optional[str | Path] = None) -> None:
        """حفظ سجل الـ metadata"""
        path = Path(path) if path else self.store_dir / "registry.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump([e.to_dict() for e in self.entries], f, indent=2, ensure_ascii=False)
        logger.info(f"تم حفظ سجل النماذج ({len(self.entries)}) في: {path}")

    def load(self, path: Optional[str | Path] = None) -> None:
        """تحميل سجل الـ metadata"""
        path = Path(path) if path else self.store_dir / "registry.json"
        if not path.exists():
            raise FileNotFoundError(f"ملف السجل غير موجود: {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.entries = [ModelEntry.from_dict(d) for d in data]
        logger.info(f"تم تحميل {len(self.entries)} نسخة نموذج من: {path}")

    def summary(self) -> Dict[str, Any]:
        """ملخص المكتبة"""
        by_status: Dict[str, int] = {}
        by_name: Dict[str, int] = {}
        for e in self.entries:
            by_status[e.status.value] = by_status.get(e.status.value, 0) + 1
            by_name[e.name] = by_name.get(e.name, 0) + 1
        return {"total": len(self.entries), "by_status": by_status, "by_name": by_name}


def _audit_outcome(audit: Any, name: str):
    """استخراج قيمة AuditOutcome بالاسم إن وُجدت، وإلا النص"""
    try:
        from audit import AuditOutcome
        return getattr(AuditOutcome, name)
    except Exception:
        return name
