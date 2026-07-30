"""
ProtonAI - Generic Model
نموذج عام يتدرّب على أي dataset (تصنيف أو تنبؤ)
يكتشف نوع المهمة تلقائياً ويعالج الميزات والهدف
"""

import pickle
import logging
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import accuracy_score, mean_absolute_error, r2_score

logger = logging.getLogger("ProtonAI.GenericModel")


class GenericModel:
    """
    نموذج عام لأي dataset.
    - يكتشف نوع المهمة تلقائياً (classification | regression) أو حسب تحديد المستخدم.
    - يعالج الميزات الرقمية والقيم المفقودة (drop | fill_mean).
    - للـ classification: يرمّز الهدف ويرجع التسميات الأصلية بالتنبؤ.
    """

    def __init__(
        self,
        feature_columns: List[str],
        target_column: str,
        task: str = "auto",
        n_estimators: int = 100,
        random_seed: int = 42,
        missing_strategy: str = "drop",
    ):
        if task not in ("auto", "classification", "regression"):
            raise ValueError("task يجب أن يكون auto أو classification أو regression")
        if missing_strategy not in ("drop", "fill_mean"):
            raise ValueError("missing_strategy يجب أن يكون drop أو fill_mean")
        if not feature_columns:
            raise ValueError("feature_columns لا يمكن أن تكون فارغة")
        self.feature_columns = list(feature_columns)
        self.target_column = target_column
        self.task = task
        self.n_estimators = n_estimators
        self.random_seed = random_seed
        self.missing_strategy = missing_strategy

        self.model = None
        self.task_: Optional[str] = None
        self.classes_: Optional[List[str]] = None
        self._means: Dict[str, float] = {}
        self.is_trained = False

    @staticmethod
    def _to_float(value: Any) -> Optional[float]:
        """تحويل آمن إلى float، يرجع None لو تعذّر"""
        if value is None or str(value).strip() == "":
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def _compute_means(self, records: List[Dict[str, Any]]) -> None:
        """حساب متوسط كل ميزة (للتعويض عند fill_mean)"""
        for col in self.feature_columns:
            vals = [self._to_float(r.get(col)) for r in records]
            vals = [v for v in vals if v is not None]
            self._means[col] = sum(vals) / len(vals) if vals else 0.0

    def _prepare(
        self, records: List[Dict[str, Any]], require_target: bool
    ) -> Tuple[List[List[float]], List[Any]]:
        """استخراج الميزات X والهدف y_raw مع ضمان التناسق"""
        if self.missing_strategy == "fill_mean" and not self._means:
            self._compute_means(records)
        X: List[List[float]] = []
        y_raw: List[Any] = []
        for r in records:
            row: List[float] = []
            skip = False
            for col in self.feature_columns:
                v = self._to_float(r.get(col))
                if v is None:
                    if self.missing_strategy == "drop":
                        skip = True
                        break
                    v = self._means.get(col, 0.0)
                row.append(v)
            if skip:
                continue
            if require_target:
                t = r.get(self.target_column)
                if t is None or str(t).strip() == "":
                    continue
                y_raw.append(t)
            X.append(row)
        return X, y_raw

    def _detect_task(self, y_raw: List[Any]) -> str:
        """إذا كل الأهداف رقمية → regression، وإلا classification"""
        for v in y_raw:
            if self._to_float(v) is None:
                return "classification"
        return "regression"

    def fit(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """تدريب النموذج مع اكتشاف نوع المهمة"""
        if not records:
            raise ValueError("بيانات التدريب فارغة")
        X, y_raw = self._prepare(records, require_target=True)
        if not X:
            raise ValueError("لا توجد عينات صالحة بعد المعالجة")

        task = self.task if self.task != "auto" else self._detect_task(y_raw)
        self.task_ = task

        if task == "classification":
            self.classes_ = sorted(set(str(v) for v in y_raw))
            y = [self.classes_.index(str(v)) for v in y_raw]
            self.model = RandomForestClassifier(
                n_estimators=self.n_estimators, random_state=self.random_seed)
        else:
            y = [float(v) for v in y_raw]
            self.model = RandomForestRegressor(
                n_estimators=self.n_estimators, random_state=self.random_seed)

        self.model.fit(np.array(X, dtype=float), np.array(y))
        self.is_trained = True
        logger.info(f"تم تدريب نموذج {task} على {len(X)} عينة")
        return {
            "task": task,
            "samples": len(X),
            "features": len(self.feature_columns),
            "classes": self.classes_,
        }

    def predict(self, records: List[Dict[str, Any]]) -> List[Any]:
        """التنبؤ (يرجع تسميات للتصنيف، أرقاماً للتنبؤ)"""
        if not self.is_trained:
            raise RuntimeError("درّب النموذج أولاً")
        X, _ = self._prepare(records, require_target=False)
        raw = self.model.predict(np.array(X, dtype=float))
        if self.task_ == "classification":
            return [self.classes_[int(i)] for i in raw]
        return [float(v) for v in raw]

    def _confusion(self, y_true: List[int], y_pred: List[int]) -> Dict[str, Dict[str, int]]:
        """مصفوفة الخلط (الصفوف=الحقيقي، الأعمدة=المتنبأ)"""
        cm = {a: {b: 0 for b in self.classes_} for a in self.classes_}
        for t, p in zip(y_true, y_pred):
            cm[self.classes_[t]][self.classes_[p]] += 1
        return cm

    def evaluate(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """تقييم النموذج حسب نوع المهمة"""
        if not self.is_trained:
            raise RuntimeError("درّب النموذج أولاً")
        X, y_raw = self._prepare(records, require_target=True)
        X_arr = np.array(X, dtype=float)

        if self.task_ == "classification":
            y = [self.classes_.index(str(v)) for v in y_raw]
            preds = self.model.predict(X_arr)
            return {
                "task": "classification",
                "accuracy": float(accuracy_score(y, preds)),
                "samples": len(X),
                "classes": self.classes_,
                "confusion": self._confusion(y, [int(p) for p in preds]),
            }
        y = np.array([float(v) for v in y_raw])
        preds = self.model.predict(X_arr)
        return {
            "task": "regression",
            "mae": float(mean_absolute_error(y, preds)),
            "r2": float(r2_score(y, preds)),
            "samples": len(X),
        }

    def save(self, path: str | Path) -> None:
        """حفظ النموذج في ملف"""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump({
                "model": self.model,
                "task_": self.task_,
                "classes_": self.classes_,
                "feature_columns": self.feature_columns,
                "target_column": self.target_column,
                "n_estimators": self.n_estimators,
                "random_seed": self.random_seed,
                "means": self._means,
                "is_trained": self.is_trained,
            }, f)
        logger.info(f"تم حفظ النموذج في: {path}")

    def load(self, path: str | Path) -> None:
        """تحميل النموذج من ملف"""
        with open(path, "rb") as f:
            d = pickle.load(f)
        self.model = d["model"]
        self.task_ = d["task_"]
        self.classes_ = d["classes_"]
        self.feature_columns = d["feature_columns"]
        self.target_column = d["target_column"]
        self.n_estimators = d["n_estimators"]
        self.random_seed = d["random_seed"]
        self._means = d["means"]
        self.is_trained = d["is_trained"]
        logger.info(f"تم تحميل النموذج من: {path}")
