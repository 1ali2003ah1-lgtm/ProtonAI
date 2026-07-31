"""
ProtonAI - Benchmark Baselines
مقارنة النموذج بنماذج معيارية "غبية" لإثبات إنه يتعلم فعلاً
تصنيف: الأكثرية + العشوائي الطبقي. تنبؤ: المتوسط + الوسيط.
"""

import math
import logging
from collections import Counter
from typing import List, Dict, Any, Tuple

logger = logging.getLogger("ProtonAI.Benchmark")


def _median(sorted_vals: List[float]) -> float:
    """الوسيط لقائمة مرتبة"""
    n = len(sorted_vals)
    if n == 0:
        raise ValueError("لا يمكن حساب الوسيط لقائمة فارغة")
    if n % 2 == 1:
        return sorted_vals[n // 2]
    return (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2.0


def _accuracy(y_true: List[Any], y_pred: List[Any]) -> float:
    """الدقة بين قائمتين"""
    n = len(y_true)
    if n == 0:
        return 0.0
    return sum(1 for t, p in zip(y_true, y_pred) if str(t) == str(p)) / n


def _mae(y_true: List[float], y_pred: List[float]) -> float:
    """متوسط الخطأ المطلق"""
    n = len(y_true)
    if n == 0:
        return 0.0
    return sum(abs(t - p) for t, p in zip(y_true, y_pred)) / n


def _mse(y_true: List[float], y_pred: List[float]) -> float:
    """متوسط مربع الخطأ"""
    n = len(y_true)
    if n == 0:
        return 0.0
    return sum((t - p) ** 2 for t, p in zip(y_true, y_pred)) / n


class BenchmarkEvaluator:
    """
    مقيّم الـ baselines.
    يبني نماذج معيارية من بيانات التدريب ويقيّمها على الاختبار،
    ثم يحسب skill score ويصدر verdict.
    """

    def majority_class_accuracy(self, y_train: List[Any], y_test: List[Any]) -> float:
        """baseline الأكثرية: يتوقع الفئة الأكثر تكراراً بالتدريب"""
        if not y_train:
            raise ValueError("y_train فارغة")
        majority = Counter(str(x) for x in y_train).most_common(1)[0][0]
        return _accuracy(y_test, [majority] * len(y_test))

    def stratified_random_expected_accuracy(
        self, y_train: List[Any], y_test: List[Any]
    ) -> float:
        """
        baseline العشوائي الطبقي (قيمة متوقعة تحليلية حتمية):
        sum_c (p_train_c * p_test_c)
        """
        if not y_train or not y_test:
            raise ValueError("y_train أو y_test فارغة")
        c_train = Counter(str(x) for x in y_train)
        c_test = Counter(str(x) for x in y_test)
        n_train, n_test = len(y_train), len(y_test)
        classes = set(c_train.keys()) | set(c_test.keys())
        return sum((c_train.get(c, 0) / n_train) * (c_test.get(c, 0) / n_test) for c in classes)

    def mean_baseline_metrics(
        self, y_train: List[Any], y_test: List[Any]
    ) -> Dict[str, float]:
        """baseline المتوسط: يتوقع متوسط التدريب دايماً"""
        if not y_train:
            raise ValueError("y_train فارغة")
        vals = [float(x) for x in y_train]
        mean = sum(vals) / len(vals)
        yt = [float(x) for x in y_test]
        return {"mae": _mae(yt, [mean] * len(yt)), "mse": _mse(yt, [mean] * len(yt)),
                "constant": mean}

    def median_baseline_metrics(
        self, y_train: List[Any], y_test: List[Any]
    ) -> Dict[str, float]:
        """baseline الوسيط: يتوقع وسيط التدريب دايماً"""
        if not y_train:
            raise ValueError("y_train فارغة")
        med = _median(sorted(float(x) for x in y_train))
        yt = [float(x) for x in y_test]
        return {"mae": _mae(yt, [med] * len(yt)), "mse": _mse(yt, [med] * len(yt)),
                "constant": med}

    def classification_skill(self, model_acc: float, baseline_acc: float) -> float:
        """
        skill score للتصنيف: (model - base) / (1 - base)
        لو base >= 1 (ما في مجال للتحسن) → 0.0
        """
        denom = 1.0 - baseline_acc
        if denom <= 1e-12:
            return 0.0
        return (model_acc - baseline_acc) / denom

    def regression_skill(self, model_mse: float, baseline_mse: float) -> float:
        """
        skill score للتنبؤ (R² style): 1 - model_mse / baseline_mse
        لو baseline_mse == 0: 1.0 لو model==0 وإلا -inf
        """
        if baseline_mse <= 1e-12:
            return 1.0 if model_mse <= 1e-12 else float("-inf")
        return 1.0 - model_mse / baseline_mse

    def classification_baselines(
        self, y_train: List[Any], y_test: List[Any]
    ) -> Dict[str, float]:
        """كل baselines التصنيف مع دقتها"""
        return {
            "majority_class": self.majority_class_accuracy(y_train, y_test),
            "stratified_random": self.stratified_random_expected_accuracy(y_train, y_test),
        }

    def regression_baselines(
        self, y_train: List[Any], y_test: List[Any]
    ) -> Dict[str, Dict[str, float]]:
        """كل baselines التنبؤ مع مقاييسها"""
        return {
            "mean": self.mean_baseline_metrics(y_train, y_test),
            "median": self.median_baseline_metrics(y_train, y_test),
        }

    def verdict(
        self, model_metrics: Dict[str, float],
        baselines: Dict[str, Any], task: str,
    ) -> Dict[str, Any]:
        """
        الحكم النهائي: هل النموذج يتغلب على كل الـ baselines؟
        classification: model accuracy > كل baseline accuracy.
        regression: model mae < كل baseline mae.
        """
        if task == "classification":
            model_val = float(model_metrics.get("accuracy", 0.0))
            beats = {name: model_val > float(acc) for name, acc in baselines.items()}
        elif task == "regression":
            model_val = float(model_metrics.get("mae", float("inf")))
            beats = {name: model_val < float(b["mae"]) for name, b in baselines.items()}
        else:
            raise ValueError(f"task غير معروف: {task}")
        beats_all = all(beats.values()) if beats else False
        logger.info(f"Verdict ({task}): beats_all={beats_all}, beats={beats}")
        return {"beats_all_baselines": beats_all, "beats": beats,
                "model_value": model_val, "task": task}
