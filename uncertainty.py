"""
ProtonAI - Uncertainty Estimation
تقدير عدم اليقين من داخل الغابة العشوائية (التباين بين الأشجار)
للتنبؤ: فواصل ثقة. للتصنيف: ثقة + إنتروبيا + هامش.
"""

import math
import logging
import numpy as np
from typing import List, Dict, Any, Optional

logger = logging.getLogger("ProtonAI.Uncertainty")


def _percentile(sorted_vals: List[float], p: float) -> float:
    """حساب المئين (استيفاء خطي)"""
    n = len(sorted_vals)
    if n == 0:
        raise ValueError("لا يمكن حساب المئين لقائمة فارغة")
    if n == 1:
        return sorted_vals[0]
    k = (n - 1) * p
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_vals[int(k)]
    return sorted_vals[f] * (c - k) + sorted_vals[c] * (k - f)


def _entropy(probs: List[float]) -> float:
    """إنتروبيا شانون (nat) لمتجه احتمالات"""
    h = 0.0
    for p in probs:
        if p > 0:
            h -= p * math.log(p)
    return h


class UncertaintyEstimator:
    """
    مستخرج عدم اليقين.
    يعمل على نموذج GenericModel مدرّب (يستخدم غابته العشوائية الداخلية).
    - regression_uncertainty: فواصل ثقة لكل عينة.
    - classification_uncertainty: ثقة/إنتروبيا/هامش لكل عينة.
    - aggregate: ملخص + نسبة العينات عالية عدم اليقين.
    """

    def __init__(self, ci: float = 0.95):
        if not (0 < ci < 1):
            raise ValueError("ci يجب أن يكون بين 0 و 1 (حصراً)")
        self.ci = ci

    def _check_model(self, model: Any) -> None:
        """التحقق من أن النموذج مدرّب وغابة عشوائية"""
        if not getattr(model, "is_trained", False):
            raise RuntimeError("النموذج غير مدرّب")
        inner = getattr(model, "model", None)
        if inner is None or not hasattr(inner, "estimators_"):
            raise ValueError("عدم اليقين يتطلب نموذج غابة عشوائية (estimators_)")

    def _prepare_X(self, model: Any, records: List[Dict[str, Any]]) -> np.ndarray:
        """استخراج مصفوفة الميزات عبر منطق النموذج نفسه"""
        X, _ = model._prepare(records, require_target=False)
        return np.array(X, dtype=float)

    def regression_uncertainty(
        self, model: Any, records: List[Dict[str, Any]]
    ) -> List[Dict[str, float]]:
        """عدم يقين تنبؤ: متوسط + انحراف الأشجار + فاصل ثقة"""
        self._check_model(model)
        if not records:
            return []
        X = self._prepare_X(model, records)
        if X.size == 0:
            return []
        # تنبؤ كل شجرة على حدة → مصفوفة (n_trees, n_samples)
        tree_preds = np.array([t.predict(X) for t in model.model.estimators_])
        alpha = (1.0 - self.ci) / 2.0
        out: List[Dict[str, float]] = []
        for col in range(tree_preds.shape[1]):
            vals = sorted(tree_preds[:, col].tolist())
            mean = float(np.mean(vals))
            std = float(np.std(vals, ddof=1)) if len(vals) > 1 else 0.0
            out.append({
                "mean": mean,
                "std": std,
                "ci_low": _percentile(vals, alpha),
                "ci_high": _percentile(vals, 1.0 - alpha),
                "n_trees": len(vals),
            })
        return out

    def classification_uncertainty(
        self, model: Any, records: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """عدم يقين تصنيف: ثقة + إنتروبيا + هامش + احتمالات"""
        self._check_model(model)
        if not records:
            return []
        X = self._prepare_X(model, records)
        if X.size == 0:
            return []
        proba = model.model.predict_proba(X)  # (n_samples, n_classes)
        classes = model.classes_ or [str(c) for c in model.model.classes_]
        out: List[Dict[str, Any]] = []
        for row in proba:
            probs = [float(p) for p in row]
            sorted_p = sorted(probs, reverse=True)
            confidence = sorted_p[0]
            margin = (sorted_p[0] - sorted_p[1]) if len(sorted_p) > 1 else sorted_p[0]
            top_idx = int(np.argmax(row))
            out.append({
                "predicted": classes[top_idx],
                "confidence": confidence,
                "entropy": _entropy(probs),
                "margin": margin,
                "class_probs": {classes[i]: probs[i] for i in range(len(classes))},
            })
        return out

    def aggregate_regression(
        self, per_sample: List[Dict[str, float]], high_threshold: float = 5.0
    ) -> Dict[str, Any]:
        """ملخص عدم يقين التنبؤ + نسبة العينات عالية عدم اليقين (بعرض الفاصل)"""
        if not per_sample:
            return {"samples": 0, "mean_std": 0.0, "mean_ci_width": 0.0,
                    "pct_high_uncertainty": 0.0, "high_threshold": high_threshold}
        stds = [s["std"] for s in per_sample]
        widths = [s["ci_high"] - s["ci_low"] for s in per_sample]
        high = sum(1 for w in widths if w > high_threshold)
        return {
            "samples": len(per_sample),
            "mean_std": float(np.mean(stds)),
            "mean_ci_width": float(np.mean(widths)),
            "pct_high_uncertainty": high / len(per_sample) * 100.0,
            "high_threshold": high_threshold,
        }

    def aggregate_classification(
        self, per_sample: List[Dict[str, Any]], low_conf_threshold: float = 0.7
    ) -> Dict[str, Any]:
        """ملخص عدم يقين التصنيف + نسبة العينات منخفضة الثقة"""
        if not per_sample:
            return {"samples": 0, "mean_confidence": 0.0, "mean_entropy": 0.0,
                    "pct_low_confidence": 0.0, "low_conf_threshold": low_conf_threshold}
        confs = [s["confidence"] for s in per_sample]
        ents = [s["entropy"] for s in per_sample]
        low = sum(1 for c in confs if c < low_conf_threshold)
        return {
            "samples": len(per_sample),
            "mean_confidence": float(np.mean(confs)),
            "mean_entropy": float(np.mean(ents)),
            "pct_low_confidence": low / len(confs) * 100.0,
            "low_conf_threshold": low_conf_threshold,
  }
