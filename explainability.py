"""
ProtonAI - Explainability
تفسير قرارات النموذج: أهمية عالمية + أهمية بالتبديل + تفسير محلي لكل عينة
يجعل النموذج "صندوقاً شفافاً" يفهمه الطبيب (بدون مكتبات خارجية ثقيلة)
"""

import math
import random
import logging
import numpy as np
from typing import List, Dict, Any, Optional, Callable

logger = logging.getLogger("ProtonAI.Explainability")


def _std(vals: List[float]) -> float:
    """الانحراف المعياري للعينة (n-1)"""
    n = len(vals)
    if n < 2:
        return 0.0
    m = sum(vals) / n
    return math.sqrt(sum((v - m) ** 2 for v in vals) / (n - 1))


def _accuracy(y_true: List[Any], y_pred: List[Any]) -> float:
    """الدقة (مقارنة نصوص)"""
    n = len(y_true)
    if n == 0:
        return 0.0
    return sum(1 for t, p in zip(y_true, y_pred) if str(t) == str(p)) / n


def _neg_mae(y_true: List[Any], y_pred: List[Any]) -> float:
    """سالب متوسط الخطأ المطلق (أعلى = أفضل، ليوحّد اتجاه الأهمية)"""
    n = len(y_true)
    if n == 0:
        return 0.0
    return -sum(abs(float(t) - float(p)) for t, p in zip(y_true, y_pred)) / n


class Explainability:
    """
    مفسّر القرارات.
    - global_importance: أهمية الميزات من الغابة العشوائية.
    - permutation_importance: أهمية بتبديل كل ميزة وقياس تدهور المقياس.
    - local_explanation: تفسير تنبؤ عينة واحدة (مساهمة تقريبية + احتمالات).
    - top_features: أهم k ميزات.
    """

    def __init__(self, seed: int = 42):
        self.seed = seed

    def _check(self, model: Any) -> None:
        """التحقق من أن النموذج مدرّب وغابة عشوائية"""
        if not getattr(model, "is_trained", False):
            raise RuntimeError("النموذج غير مدرّب")
        if not hasattr(getattr(model, "model", None), "feature_importances_"):
            raise ValueError("التفسير يتطلب نموذجاً شجرياً (feature_importances_)")

    def _default_metric(self, task: Optional[str]) -> Callable:
        """المقياس الافتراضي حسب نوع المهمة (higher-is-better)"""
        return _accuracy if task == "classification" else _neg_mae

    def global_importance(self, model: Any) -> Dict[str, float]:
        """أهمية الميزات العالمية (من الغابة العشوائية)"""
        self._check(model)
        imp = model.model.feature_importances_
        feats = model.feature_columns
        return {f: float(imp[i]) for i, f in enumerate(feats)}

    def top_features(self, model: Any, k: int = 5) -> List[Dict[str, Any]]:
        """أهم k ميزات مرتبة تنازلياً"""
        if k < 1:
            raise ValueError("k يجب أن يكون >= 1")
        imp = self.global_importance(model)
        ranked = sorted(imp.items(), key=lambda kv: kv[1], reverse=True)[:k]
        return [{"feature": name, "importance": val} for name, val in ranked]

    def permutation_importance(
        self, model: Any, records: List[Dict[str, Any]], target: str,
        n_repeats: int = 5, metric: Optional[Callable] = None,
    ) -> Dict[str, Dict[str, float]]:
        """
        أهمية كل ميزة بتبديل قيمها وقياس تدهور المقياس.
        drop موجب = الميزة مهمة (التبديل أضرّ بالأداء).
        """
        self._check(model)
        if not records:
            raise ValueError("records فارغة")
        if n_repeats < 1:
            raise ValueError("n_repeats يجب أن يكون >= 1")
        rng = random.Random(self.seed)
        y_true = [r[target] for r in records]
        metric = metric or self._default_metric(model.task_)
        base_score = metric(y_true, model.predict(records))

        result: Dict[str, Dict[str, float]] = {}
        for f in model.feature_columns:
            drops: List[float] = []
            for _ in range(n_repeats):
                vals = [r.get(f) for r in records]
                shuffled = vals[:]
                rng.shuffle(shuffled)
                perm = [dict(r) for r in records]  # نسخ سطحية آمنة
                for i, r in enumerate(perm):
                    r[f] = shuffled[i]
                perm_score = metric(y_true, model.predict(perm))
                drops.append(base_score - perm_score)
            result[f] = {"mean": sum(drops) / len(drops), "std": _std(drops)}
        logger.info(f"permutation_importance اكتمل على {len(records)} عينة")
        return result

    def local_explanation(
        self, model: Any, record: Dict[str, Any],
        reference: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        تفسير تنبؤ عينة واحدة.
        - regression: approx_contribution = تأثير استبدال الميزة بقيمة مرجعية.
        - classification: class_probabilities + أهمية كل ميزة.
        """
        self._check(model)
        imp = self.global_importance(model)
        base_pred = model.predict([record])[0]
        features_out: List[Dict[str, Any]] = []
        for f in model.feature_columns:
            val = record.get(f)
            contrib = None
            if (model.task_ == "regression" and reference is not None and f in reference):
                mod = dict(record)
                mod[f] = reference[f]
                contrib = float(base_pred) - float(model.predict([mod])[0])
            features_out.append({
                "feature": f, "value": val,
                "global_importance": imp.get(f, 0.0),
                "approx_contribution": contrib,
            })

        out: Dict[str, Any] = {"task": model.task_, "predicted": base_pred, "features": features_out}
        if model.task_ == "classification":
            try:
                X, _ = model._prepare([record], require_target=False)
                proba = model.model.predict_proba(np.array(X, dtype=float))[0]
                classes = model.classes_ or [str(c) for c in model.model.classes_]
                out["class_probabilities"] = {classes[i]: float(proba[i]) for i in range(len(classes))}
            except Exception:
                out["class_probabilities"] = {}
        return out
