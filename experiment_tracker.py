"""
ProtonAI - Experiment Tracker
تتبّع التجارب القابل لإعادة الإنتاج + تثبيت تقسيمات البيانات
يربط كل تجربة بـ config + بصمة البيانات + البذرة + المقاييس
"""

import json
import hashlib
import logging
import random
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger("ProtonAI.ExperimentTracker")


def fingerprint(data: Any) -> str:
    """بصمة SHA-256 حتمية لأي بيانات (قابلة لإعادة الإنتاج)"""
    text = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def stable_split(
    records: List[Dict[str, Any]], train_ratio: float = 0.8, seed: int = 42
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], str]:
    """
    تقسيم حتمي: نفس records + نفس seed + نفس ratio = نفس التقسيم دايماً.
    يرجع (train, test, split_fingerprint).
    """
    if not (0 < train_ratio <= 1.0):
        raise ValueError("train_ratio يجب أن يكون بين 0 و 1")
    rng = random.Random(seed)
    indexed = list(enumerate(records))
    rng.shuffle(indexed)
    n = int(len(indexed) * train_ratio)
    train = [records[i] for i, _ in indexed[:n]]
    test = [records[i] for i, _ in indexed[n:]]
    fp = fingerprint({
        "seed": seed, "ratio": train_ratio,
        "data": fingerprint(records), "n": len(records),
    })
    return train, test, fp


@dataclass
class Experiment:
    """تجربة واحدة قابلة لإعادة الإنتاج"""
    experiment_id: str
    name: str
    config: Dict[str, Any]
    data_fingerprint: str
    split_fingerprint: str = ""
    seed: int = 42
    metrics: Dict[str, Any] = field(default_factory=dict)
    model_fingerprint: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ExperimentTracker:
    """
    متتبّع التجارب.
    - register: يسجّل تجربة جديدة ببصمة البيانات.
    - verify: يتأكد إن التجربة قابلة لإعادة الإنتاج (بصمات مطابقة).
    - find_by_data / best: استعلامات.
    - save / load: حفظ السجل.
    """

    def __init__(self):
        self.experiments: List[Experiment] = []

    def register(
        self, name: str, config: Dict[str, Any], data: Any,
        metrics: Optional[Dict[str, Any]] = None,
        split_fingerprint: str = "", model_fingerprint: str = "",
        seed: int = 42, notes: str = "",
    ) -> Experiment:
        """تسجيل تجربة جديدة"""
        exp = Experiment(
            experiment_id=hashlib.sha256(
                (name + datetime.now().isoformat() + str(len(self.experiments))).encode()
            ).hexdigest()[:12],
            name=name, config=dict(config),
            data_fingerprint=fingerprint(data),
            split_fingerprint=split_fingerprint, seed=seed,
            metrics=dict(metrics or {}), model_fingerprint=model_fingerprint,
            notes=notes,
        )
        self.experiments.append(exp)
        logger.info(f"تم تسجيل التجربة {exp.experiment_id} ({name})")
        return exp

    def verify(self, experiment_id: str, data: Any, split_fingerprint: str = "") -> bool:
        """التحقق من قابلية إعادة الإنتاج: بصمة البيانات (والـ split إن مُرّر) مطابقة"""
        for exp in self.experiments:
            if exp.experiment_id == experiment_id:
                if fingerprint(data) != exp.data_fingerprint:
                    return False
                if split_fingerprint and split_fingerprint != exp.split_fingerprint:
                    return False
                return True
        return False

    def find_by_data(self, data: Any) -> List[Experiment]:
        """كل التجارب على نفس البيانات"""
        fp = fingerprint(data)
        return [e for e in self.experiments if e.data_fingerprint == fp]

    def list_all(self) -> List[Experiment]:
        """كل التجارب المسجّلة"""
        return list(self.experiments)

    def best(self, metric: str, higher_better: bool = True) -> Optional[Experiment]:
        """أفضل تجربة حسب مقياس"""
        candidates = [e for e in self.experiments if metric in e.metrics]
        if not candidates:
            return None
        return (max(candidates, key=lambda e: e.metrics[metric]) if higher_better
                else min(candidates, key=lambda e: e.metrics[metric]))

    def save(self, path: str | Path) -> None:
        """حفظ سجل التجارب"""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump([e.to_dict() for e in self.experiments], f, indent=2, ensure_ascii=False)
        logger.info(f"تم حفظ سجل التجارب ({len(self.experiments)}) في: {path}")

    def load(self, path: str | Path) -> None:
        """تحميل سجل التجارب"""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"ملف التجارب غير موجود: {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.experiments = [Experiment(**d) for d in data]
        logger.info(f"تم تحميل {len(self.experiments)} تجربة من: {path}")
