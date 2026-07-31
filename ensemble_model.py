"""
ProtonAI - Ensemble Model
تجميع عدة نماذج: تصويت ناعم للتصنيف + متوسط للتنبؤ + عدم يقين التجميع
أدق وأثبت من أي نموذج لوحده (مبدأ الفائزين بالمسابقات العالمية)
"""

import pickle
import logging
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional

from sklearn.metrics import accuracy_score, mean_absolute_error, r2_score
from generic_model import GenericModel

logger = logging.getLogger("ProtonAI.EnsembleModel")


class EnsembleModel:
    """
    تجميع نماذج GenericModel.
    - configs: قائمة إعدادات، كل واحد يبني نموذجاً. لو None → 3 نماذج ببذور مختلفة.
    - fit: يدرّب كل النماذج.
    - predict: تصويت ناعم (تصنيف) / متوسط (تنبؤ).
    - predict_with_uncertainty: متوسط + انحراف + فاصل ثقة بين النماذج (تنبؤ).
    - predict_proba_ensemble: متوسط احتمالات الفئات (تصنيف).
    """

    def __init__(
        self,
        feature_columns: List[str],
        target_column: str,
        configs: Optional[List[Dict[str, Any]]] = None,
        task: str = "auto",
        seed: int = 42,
        ci: float = 0.95,
    ):
        if not feature_columns:
            raise ValueError("feature_columns لا يمكن أن تكون فارغة")
        if not (0 < ci < 1):
            raise ValueError("ci يجب أن يكون بين 0 و 1 (حصراً)")
        self.feature_columns = list(feature_columns)
        self.target_column = target_column
        self.task = task
        self.seed = seed
        self.ci = ci
        self.configs = list(configs) if configs else [
            {"n_estimators": 50, "random_seed": seed + i} for i in range(3)
        ]
        if not self.configs:
            raise ValueError("configs لا يمكن أن تكون فارغة")
        self.models: List[GenericModel] = []
        self.task_: Optional[str] = None
        self.is_trained = False

    def _build(self, config: Dict[str, Any]) -> GenericModel:
        """بناء نموذج واحد من config مع بذرة حتمية"""
        kwargs = {
            "feature_columns": self.feature_columns,
            "target_column": self.target_column,
            "task": self.task,
            "random_seed": self.seed,
        }
        for k in ("n_estimators", "random_seed", "missing_strategy", "task"):
            if k in config:
                kwargs[k] = config[k]
        return GenericModel(**kwargs)

    def fit(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """تدريب كل النماذج"""
        if not records:
            raise ValueError("بيانات التدريب فارغة")
        self.models = []
        for cfg in self.configs:
            m = self._build(cfg)
            m.fit(records)
            self.models.append(m)
        self.task_ = self.models[0].task_
        self.is_trained = True
        logger.info(f"تم تدريب ensemble من {len(self.models)} نموذج ({self.task_})")
        return {"n_models": len(self.models), "task": self.task_, "samples": len(records)}

    def _check(self) -> None:
        if not self.is_trained:
            raise RuntimeError("درّب الـ ensemble أولاً")

    def _prepare_X(self, records: List[Dict[str, Any]]) -> np.ndarray:
        """مصفوفة الميزات (عبر أول نموذج، الميزات مشتركة)"""
        X, _ = self.models[0]._prepare(records, require_target=False)
        return np.array(X, dtype=float)

    def _union_classes(self) -> List[str]:
        """اتحاد مرتّب للفئات عبر كل النماذج"""
        classes = set()
        for m in self.models:
            src = m.classes_ if m.classes_ else [str(c) for c in m.model.classes_]
            classes.update(src)
        return sorted(classes, key=str)

    def predict(self, records: List[Dict[str, Any]]) -> List[Any]:
        """التنبؤ المجمّع"""
        self._check()
        if not records:
            return []
        X = self._prepare_X(records)
        if X.size == 0:
            return []
        if self.task_ == "classification":
            union = self._union_classes()
            mean_proba = np.zeros((len(X), len(union)))
            for m in self.models:
                proba = m.model.predict_proba(X)
                local = m.classes_ if m.classes_ else [str(c) for c in m.model.classes_]
                for j, c in enumerate(local):
                    mean_proba[:, union.index(c)] += proba[:, j]
            mean_proba /= len(self.models)
            idx = mean_proba.argmax(axis=1)
            return [union[i] for i in idx]
        preds = np.array([m.model.predict(X) for m in self.models])
        return preds.mean(axis=0).tolist()

    def predict_proba_ensemble(
        self, records: List[Dict[str, Any]]
    ) -> List[Dict[str, float]]:
        """متوسط احتمالات الفئات عبر النماذج (تصنيف فقط)"""
        self._check()
        if self.task_ != "classification":
            raise RuntimeError("predict_proba_ensemble للتصنيف فقط")
        if not records:
            return []
        X = self._prepare_X(records)
        if X.size == 0:
            return []
        union = self._union_classes()
        mean_proba = np.zeros((len(X), len(union)))
        for m in self.models:
            proba = m.model.predict_proba(X)
            local = m.classes_ if m.classes_ else [str(c) for c in m.model.classes_]
            for j, c in enumerate(local):
                mean_proba[:, union.index(c)] += proba[:, j]
        mean_proba /= len(self.models)
        return [{union[j]: float(mean_proba[i, j]) for j in range(len(union))}
                for i in range(len(X))]

    def predict_with_uncertainty(
        self, records: List[Dict[str, Any]]
    ) -> List[Dict[str, float]]:
        """عدم يقين التجميع: متوسط + انحراف + فاصل ثقة بين النماذج (تنبؤ فقط)"""
        self._check()
        if self.task_ != "regression":
            raise RuntimeError("predict_with_uncertainty للتنبؤ فقط")
        if not records:
            return []
        X = self._prepare_X(records)
        if X.size == 0:
            return []
        preds = np.array([m.model.predict(X) for m in self.models])  # (n_models, n)
        alpha = (1.0 - self.ci) / 2.0
        out: List[Dict[str, float]] = []
        for col in range(preds.shape[1]):
            col_vals = preds[:, col]
            mean = float(col_vals.mean())
            std = float(col_vals.std(ddof=1)) if preds.shape[0] > 1 else 0.0
            out.append({
                "mean": mean, "std": std,
                "ci_low": float(np.percentile(col_vals, alpha * 100)),
                "ci_high": float(np.percentile(col_vals, (1 - alpha) * 100)),
                "n_models": preds.shape[0],
            })
        return out

    def evaluate(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """تقييم التجميع"""
        self._check()
        y_pred = self.predict(records)
        y_true = [r[self.target_column] for r in records]
        if self.task_ == "classification":
            return {"task": "classification",
                    "accuracy": float(accuracy_score(
                        [str(t) for t in y_true], [str(p) for p in y_pred])),
                    "n_models": len(self.models), "samples": len(records)}
        yt = np.array([float(t) for t in y_true])
        yp = np.array([float(p) for p in y_pred])
        return {"task": "regression",
                "mae": float(mean_absolute_error(yt, yp)),
                "r2": float(r2_score(yt, yp)),
                "n_models": len(self.models), "samples": len(records)}

    def save(self, path: str | Path) -> None:
        """حفظ الـ ensemble (كل النماذج)"""
        self._check()
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        states = []
        for m in self.models:
            states.append({
                "model": m.model, "task_": m.task_, "classes_": m.classes_,
                "feature_columns": m.feature_columns, "target_column": m.target_column,
                "n_estimators": m.n_estimators, "random_seed": m.random_seed,
                "means": m._means, "is_trained": m.is_trained,
            })
        with open(path, "wb") as f:
            pickle.dump({
                "states": states, "task_": self.task_, "configs": self.configs,
                "feature_columns": self.feature_columns, "target_column": self.target_column,
                "seed": self.seed, "ci": self.ci, "task": self.task,
            }, f)
        logger.info(f"تم حفظ الـ ensemble ({len(states)} نموذج) في: {path}")

    def load(self, path: str | Path) -> None:
        """تحميل الـ ensemble"""
        with open(path, "rb") as f:
            d = pickle.load(f)
        self.configs = d["configs"]
        self.feature_columns = d["feature_columns"]
        self.target_column = d["target_column"]
        self.seed = d["seed"]
        self.ci = d["ci"]
        self.task = d["task"]
        self.task_ = d["task_"]
        self.models = []
        for s in d["states"]:
            m = GenericModel(s["feature_columns"], s["target_column"])
            m.model = s["model"]
            m.task_ = s["task_"]
            m.classes_ = s["classes_"]
            m.n_estimators = s["n_estimators"]
            m.random_seed = s["random_seed"]
            m._means = s["means"]
            m.is_trained = s["is_trained"]
            self.models.append(m)
        self.is_trained = True
        logger.info(f"تم تحميل الـ ensemble ({len(self.models)} نموذج) من: {path}")
