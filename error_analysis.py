"""
ProtonAI - Error Analysis
تحليل الأخطاء: أين يخطئ النموذج، ولماذا، وأي الحالات أخطر سريرياً
يربط الأخطاء بعدم اليقين لكشف ما إذا كانت المنصة "تعرف حدودها"
"""

import math
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("ProtonAI.ErrorAnalysis")


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


def _pearson(xs: List[float], ys: List[float]) -> float:
    """ارتباط بيرسون (يدوي، بدون مكتبات خارجية)"""
    n = len(xs)
    if n < 2:
        return 0.0
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((xs[i] - mx) * (ys[i] - my) for i in range(n))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx == 0 or dy == 0:
        return 0.0
    return num / (dx * dy)


def _bin_index(value: float, lo: float, hi: float, n_bins: int) -> int:
    """رقم الخانة (bin) لقيمة ضمن مدى مقسّم لـ n_bins"""
    if hi == lo:
        return 0
    idx = int((value - lo) / (hi - lo) * n_bins)
    return min(max(idx, 0), n_bins - 1)


def _pick(record: Dict[str, Any], feature_keys: Optional[List[str]]) -> Dict[str, Any]:
    """استخراج ميزات محددة من سجل (لعرض أسوأ الحالات)"""
    if not feature_keys:
        return {}
    return {k: record.get(k) for k in feature_keys if k in record}


class ErrorAnalyzer:
    """
    محلّل الأخطاء.
    - analyze_classification: خلط + خطأ لكل فئة + أسوأ الحالات (واثق+غلط) + حدودية.
    - analyze_regression: أسوأ الحالات + تحيز + أخطاء سريرية خطيرة + خطأ حسب نطاق الهدف.
    - correlate_with_uncertainty: هل الأخطاء تتركز بالعينات عالية عدم اليقين؟
    """

    def __init__(self, tolerance: float = 3.0, n_bins: int = 3, top_k: int = 5):
        if tolerance <= 0:
            raise ValueError("tolerance يجب أن يكون > 0")
        if n_bins < 1:
            raise ValueError("n_bins يجب أن يكون >= 1")
        if top_k < 1:
            raise ValueError("top_k يجب أن يكون >= 1")
        self.tolerance = tolerance
        self.n_bins = n_bins
        self.top_k = top_k

    def analyze_classification(
        self,
        y_true: List[Any],
        y_pred: List[Any],
        records: Optional[List[Dict[str, Any]]] = None,
        per_sample: Optional[List[Dict[str, Any]]] = None,
        feature_keys: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """تحليل أخطاء التصنيف"""
        if len(y_true) != len(y_pred):
            raise ValueError("y_true و y_pred بطول مختلف")
        n = len(y_true)
        records = records if records is not None else [{}] * n
        per_sample = per_sample if per_sample is not None else [{}] * n
        if not (len(records) == n and len(per_sample) == n):
            raise ValueError("records/per_sample يجب أن تطابق طول y_true")

        classes = sorted(set([str(t) for t in y_true] + [str(p) for p in y_pred]), key=str)
        cm = {a: {b: 0 for b in classes} for a in classes}
        errors: List[Dict[str, Any]] = []

        for i in range(n):
            t, p = str(y_true[i]), str(y_pred[i])
            cm[t][p] += 1
            if t != p:
                err = {"index": i, "true": t, "predicted": p,
                       "record": _pick(records[i], feature_keys)}
                conf = per_sample[i].get("confidence")
                if conf is not None:
                    err["confidence"] = float(conf)
                errors.append(err)

        # خطأ لكل فئة
        per_class = {}
        for c in classes:
            total_c = sum(cm[c].values())
            correct_c = cm[c].get(c, 0)
            per_class[c] = {
                "total": total_c, "correct": correct_c,
                "error_rate": (1.0 - correct_c / total_c) if total_c else 0.0,
            }

        # أسوأ الحالات: الأخطاء الواثقة أولاً (الأخطر: واثق + غلط)
        if any("confidence" in e for e in errors):
            worst = sorted(errors, key=lambda e: e.get("confidence", 0.0), reverse=True)[:self.top_k]
        else:
            worst = errors[:self.top_k]

        # الحالات الحدودية (ثقة منخفضة، صح أو غلط)
        borderline = []
        for i in range(n):
            conf = per_sample[i].get("confidence")
            if conf is not None and conf < 0.7:
                borderline.append({"index": i, "true": str(y_true[i]),
                                   "predicted": str(y_pred[i]), "confidence": float(conf)})

        accuracy = (n - len(errors)) / n if n else 0.0
        return {
            "task": "classification", "n": n, "n_errors": len(errors),
            "accuracy": accuracy, "confusion": cm, "per_class_error": per_class,
            "worst_cases": worst, "borderline_count": len(borderline),
            "borderline": borderline[:self.top_k],
        }

    def analyze_regression(
        self,
        y_true: List[Any],
        y_pred: List[Any],
        records: Optional[List[Dict[str, Any]]] = None,
        per_sample: Optional[List[Dict[str, Any]]] = None,
        feature_keys: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """تحليل أخطاء التنبؤ"""
        if len(y_true) != len(y_pred):
            raise ValueError("y_true و y_pred بطول مختلف")
        n = len(y_true)
        records = records if records is not None else [{}] * n
        per_sample = per_sample if per_sample is not None else [{}] * n

        if n == 0:
            return {"task": "regression", "n": 0, "mean_abs_error": 0.0, "bias": 0.0,
                    "max_abs_error": 0.0, "n_clinically_dangerous": 0,
                    "pct_clinically_dangerous": 0.0, "worst_cases": [],
                    "by_target_range": {}, "tolerance": self.tolerance}

        abs_err = [abs(float(y_pred[i]) - float(y_true[i])) for i in range(n)]
        signed_err = [float(y_pred[i]) - float(y_true[i]) for i in range(n)]
        bias = sum(signed_err) / n
        mean_abs = sum(abs_err) / n

        # أسوأ الحالات (أكبر خطأ مطلق)
        order = sorted(range(n), key=lambda i: abs_err[i], reverse=True)
        worst = []
        for i in order[:self.top_k]:
            w = {"index": i, "true": float(y_true[i]), "predicted": float(y_pred[i]),
                 "abs_error": abs_err[i], "record": _pick(records[i], feature_keys)}
            ciw = per_sample[i].get("ci_width")
            if ciw is not None:
                w["ci_width"] = float(ciw)
            worst.append(w)

        # الأخطاء السريرية الخطيرة (خارج التسامح)
        dangerous = [{"index": i, "abs_error": abs_err[i],
                      "true": float(y_true[i]), "predicted": float(y_pred[i])}
                     for i in range(n) if abs_err[i] > self.tolerance]

        # الخطأ حسب نطاق الهدف (يكشف هل يخطئ أكثر بالقيم العالية)
        vals = [float(v) for v in y_true]
        lo, hi = min(vals), max(vals)
        bins = {b: [] for b in range(self.n_bins)}
        for i in range(n):
            bins[_bin_index(vals[i], lo, hi, self.n_bins)].append(abs_err[i])
        by_range = {f"bin_{b}": {"count": len(bins[b]),
                    "mean_abs_error": (sum(bins[b]) / len(bins[b])) if bins[b] else 0.0}
                    for b in range(self.n_bins)}

        return {
            "task": "regression", "n": n, "mean_abs_error": mean_abs, "bias": bias,
            "max_abs_error": max(abs_err), "n_clinically_dangerous": len(dangerous),
            "pct_clinically_dangerous": len(dangerous) / n * 100.0,
            "worst_cases": worst, "by_target_range": by_range, "tolerance": self.tolerance,
        }

    def correlate_with_uncertainty(
        self, abs_errors: List[float], uncertainties: List[float]
    ) -> Dict[str, Any]:
        """
        هل الأخطاء تتركز بالعينات عالية عدم اليقين؟
        ارتباط موجب = المنصة "تعرف حدودها" (well-calibrated).
        """
        if len(abs_errors) != len(uncertainties):
            raise ValueError("abs_errors و uncertainties بطول مختلف")
        n = len(abs_errors)
        if n < 2:
            return {"n": n, "pearson": 0.0, "mean_error_high_unc": 0.0,
                    "mean_error_low_unc": 0.0, "ratio": 0.0, "well_calibrated": False}
        ae = [float(x) for x in abs_errors]
        un = [float(x) for x in uncertainties]
        r = _pearson(ae, un)
        med = _percentile(sorted(un), 0.5)
        high = [ae[i] for i in range(n) if un[i] >= med]
        low = [ae[i] for i in range(n) if un[i] < med]
        mh = sum(high) / len(high) if high else 0.0
        ml = sum(low) / len(low) if low else 0.0
        ratio = (mh / ml) if ml > 0 else (float("inf") if mh > 0 else 0.0)
        return {"n": n, "pearson": r, "mean_error_high_unc": mh,
                "mean_error_low_unc": ml, "ratio": ratio, "well_calibrated": r > 0.0}
