"""
ProtonAI - Dataset Loader
تحميل مجموعات البيانات المعتمدة (CSV/JSON) بصيغة موحّدة جاهزة للنماذج
"""

import csv
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger("ProtonAI.DatasetLoader")


class DatasetLoader:
    """
    محمّل مجموعات البيانات العام.
    - load: يقرأ CSV أو JSON → قائمة قواميس.
    - extract: يفصل الميزات (X) عن الهدف (y) كمصفوفات رقمية.
    - يتعامل مع القيم المفقودة (drop أو fill_mean).
    """

    def __init__(
        self,
        feature_columns: List[str],
        target_column: str,
        missing_strategy: str = "drop",
    ):
        if missing_strategy not in ("drop", "fill_mean"):
            raise ValueError("missing_strategy يجب أن يكون drop أو fill_mean")
        if not feature_columns:
            raise ValueError("feature_columns لا يمكن أن تكون فارغة")
        self.feature_columns = list(feature_columns)
        self.target_column = target_column
        self.missing_strategy = missing_strategy

    def load(self, path: str | Path) -> List[Dict[str, Any]]:
        """قراءة ملف CSV أو JSON وإرجاع قائمة قواميس"""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"الملف غير موجود: {p}")
        suffix = p.suffix.lower()
        if suffix == ".csv":
            with open(p, "r", encoding="utf-8", newline="") as f:
                rows = list(csv.DictReader(f))
        elif suffix == ".json":
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
                rows = data if isinstance(data, list) else [data]
        else:
            raise ValueError(f"صيغة غير مدعومة: {suffix} (استخدم .csv أو .json)")
        logger.info(f"تم تحميل {len(rows)} صف من {p.name}")
        return rows

    @staticmethod
    def _to_float(value: Any) -> Optional[float]:
        """تحويل آمن إلى float، يرجع None لو تعذّر"""
        if value is None or str(value).strip() == "":
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def extract(
        self, records: List[Dict[str, Any]]
    ) -> Tuple[List[List[float]], List[float]]:
        """
        فصل الميزات X عن الهدف y كمصفوفات رقمية.
        يتعامل مع القيم المفقودة حسب missing_strategy.
        """
        means: Dict[str, float] = {}
        if self.missing_strategy == "fill_mean":
            for col in self.feature_columns:
                vals = [self._to_float(r.get(col)) for r in records]
                vals = [v for v in vals if v is not None]
                means[col] = sum(vals) / len(vals) if vals else 0.0

        X: List[List[float]] = []
        y: List[float] = []
        for r in records:
            target = self._to_float(r.get(self.target_column))
            if target is None:
                continue
            row: List[float] = []
            skip = False
            for col in self.feature_columns:
                v = self._to_float(r.get(col))
                if v is None:
                    if self.missing_strategy == "drop":
                        skip = True
                        break
                    v = means.get(col, 0.0)
                row.append(v)
            if skip:
                continue
            X.append(row)
            y.append(target)
        logger.info(f"تم استخراج {len(X)} عينة صالحة ({len(self.feature_columns)} ميزة)")
        return X, y

    def summary(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """ملخص سريع للمجموعة"""
        return {
            "rows": len(records),
            "feature_columns": self.feature_columns,
            "target_column": self.target_column,
            "columns_found": sorted({k for r in records for k in r.keys()}) if records else [],
  }
