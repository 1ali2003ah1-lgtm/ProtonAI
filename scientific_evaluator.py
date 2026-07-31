"""
ProtonAI - Scientific Evaluator
التقييم العلمي: cross-validation بطبقات + فواصل ثقة Bootstrap + مقاييس شاملة
"""

import math
import random
import logging
import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Callable, Tuple

from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, mean_absolute_error, mean_squared_error, r2_score,
)

logger = logging.getLogger("ProtonAI.ScientificEvaluator")


@dataclass
class MetricCI:
    """قيمة مقياس مع فاصل ثقة"""
    mean: float
    std: float
    ci_low: float
    ci_high: float
    n_bootstrap: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mean": self.mean, "std": self.std,
            "ci_low": self.ci_low, "ci_high": self.ci_high,
            "n_bootstrap": self.n_bootstrap,
        }


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


def _std(vals: List[float]) -> float:
    """الانحراف المعياري للعينة (n-1)، يرجع 0 لو قيمة وحدة"""
    n = len(vals)
    if n < 2:
        return 0.0
    m = sum(vals) / n
    return math.sqrt(sum((v - m) ** 2 for v in vals) / (n - 1))


def bootstrap_ci(
    values: List[float], n_bootstrap: int = 1000,
    ci: float = 0.95, seed: int = 42,
) -> MetricCI:
    """فاصل ثقة بطريقة Bootstrap (percentile) على قائمة أرقام"""
    arr = [float(v) for v in values]
    if not arr:
        raise ValueError("bootstrap_ci يحتاج قائمة غير فارغة")
    mean = sum(arr) / len(arr)
    std = _std(arr)
    if len(arr) < 2:
        return MetricCI(mean=mean, std=0.0, ci_low=mean, ci_high=mean, n_bootstrap=n_bootstrap)
    rng = random.Random(seed)
    boot_means = []
    k = len(arr)
    for _ in range(n_bootstrap):
        sample = rng.choices(arr, k=k)
        boot_means.append(sum(sample) / k)
    boot_means.sort()
    alpha = (1.0 - ci) / 2.0
    return MetricCI(
        mean=mean, std=std,
        ci_low=_percentile(boot_means, alpha),
        ci_high=_percentile(boot_means, 1.0 - alpha),
        n_bootstrap=n_bootstrap,
    )


def bootstrap_metric_ci(
    y_true: List[Any], y_pred: List[Any], metric_fn: Callable,
    n_bootstrap: int = 1000, ci: float = 0.95, seed: int = 42,
) -> MetricCI:
    """فاصل ثقة لمقياس بإعادة أخذ عينات من أزواج (الحقيقي, المتنبأ)"""
    pairs = list(zip(y_true, y_pred))
    if not pairs:
        raise ValueError("bootstrap_metric_ci يحتاج بيانات غير فارغة")
    point = float(metric_fn(y_true, y_pred))
    rng = random.Random(seed)
    values = []
    for _ in range(n_bootstrap):
        sample = rng.choices(pairs, k=len(pairs))
        yt = [s[0] for s in sample]
        yp = [s[1] for s in sample]
        values.append(float(metric_fn(yt, yp)))
    values.sort()
    alpha = (1.0 - ci) / 2.0
    return MetricCI(
        mean=point, std=_std(values),
        ci_low=_percentile(values, alpha),
        ci_high=_percentile(values, 1.0 - alpha),
        n_bootstrap=n_bootstrap,
    )


class ScientificEvaluator:
    """
    المقيّم العلمي.
    - evaluate_classification / evaluate_regression: مقاييس شاملة.
    - cross_validate: k-fold (بطبقات اختيارياً) مع متوسط وانحراف وفاصل ثقة.
    - compare_models: يقارن عدة نماذج ويرتبها.
    """

    def __init__(self, random_seed: int = 42, n_bootstrap: int = 1000, ci: float = 0.95):
        self.seed = random_seed
        self.n_bootstrap = n_bootstrap
        self.ci = ci

    def evaluate_classification(self, y_true: List[Any], y_pred: List[Any]) -> Dict[str, Any]:
        """مقاييس تصنيف شاملة (macro-averaged)"""
        if not y_true:
            raise ValueError("y_true فارغة")
        classes = sorted(set(list(y_true) + list(y_pred)), key=str)
        cm = confusion_matrix(y_true, y_pred, labels=classes).tolist()
        return {
            "task": "classification",
            "accuracy": float(accuracy_score(y_true, y_pred)),
            "precision_macro": float(precision_score(
                y_true, y_pred, labels=classes, average="macro", zero_division=0)),
            "recall_macro": float(recall_score(
                y_true, y_pred, labels=classes, average="macro", zero_division=0)),
            "f1_macro": float(f1_score(
                y_true, y_pred, labels=classes, average="macro", zero_division=0)),
            "classes": [str(c) for c in classes],
            "confusion": cm,
            "samples": len(y_true),
        }

    def evaluate_regression(
        self, y_true: List[Any], y_pred: List[Any], tolerance: float = 3.0
    ) -> Dict[str, Any]:
        """مقاييس تنبؤ شاملة + القبول السريري"""
        if not y_true:
            raise ValueError("y_true فارغة")
        yt = np.array(y_true, dtype=float)
        yp = np.array(y_pred, dtype=float)
        within = float(np.mean(np.abs(yt - yp) <= tolerance)) * 100.0
        return {
            "task": "regression",
            "mae": float(mean_absolute_error(yt, yp)),
            "rmse": float(math.sqrt(mean_squared_error(yt, yp))),
            "r2": float(r2_score(yt, yp)),
            "clinical_acceptance_pct": within,
            "tolerance": tolerance,
            "samples": len(y_true),
        }

    def _make_folds(
        self, records: List[Dict[str, Any]], k: int,
        stratify: bool, stratify_key: Optional[str],
    ) -> List[Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]]:
        """تقسيم k-fold (بطبقات إن طُلب)"""
        n = len(records)
        rng = random.Random(self.seed)
        fold_ids: List[List[int]] = [[] for _ in range(k)]
        if stratify and stratify_key:
            groups: Dict[Any, List[int]] = {}
            for i, r in enumerate(records):
                groups.setdefault(r.get(stratify_key), []).append(i)
            for idx_list in groups.values():
                shuffled = idx_list[:]
                rng.shuffle(shuffled)
                for j, idx in enumerate(shuffled):
                    fold_ids[j % k].append(idx)
        else:
            shuffled = list(range(n))
            rng.shuffle(shuffled)
            for j, idx in enumerate(shuffled):
                fold_ids[j % k].append(idx)

        folds = []
        for i in range(k):
            test_set = set(fold_ids[i])
            train = [records[j] for j in range(n) if j not in test_set]
            test = [records[j] for j in fold_ids[i]]
            folds.append((train, test))
        return folds

    def cross_validate(
        self, records: List[Dict[str, Any]], model_factory: Callable,
        k: int = 5, stratify: bool = False, stratify_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        تقييم k-fold: يرجع مقاييس كل fold + المتوسط + الانحراف + فاصل الثقة.
        model_factory: callable يرجع نموذجاً جديداً (له fit/evaluate).
        """
        n = len(records)
        if n < k:
            raise ValueError(f"البيانات ({n}) أقل من عدد الـ folds ({k})")
        folds = self._make_folds(records, k, stratify, stratify_key)

        per_fold: List[Dict[str, Any]] = []
        task = None
        for train, test in folds:
            model = model_factory()
            info = model.fit(train)
            if task is None:
                task = getattr(model, "task_", None) or info.get("task")
            per_fold.append(model.evaluate(test))

        # تجميع المقاييس الرقمية المشتركة
        numeric_keys = sorted({
            key for ev in per_fold
            for key, val in ev.items() if isinstance(val, (int, float))
        })
        mean_metrics, std_metrics, ci_metrics = {}, {}, {}
        for key in numeric_keys:
            vals = [float(ev[key]) for ev in per_fold]
            ci = bootstrap_ci(vals, self.n_bootstrap, self.ci, self.seed)
            mean_metrics[key] = ci.mean
            std_metrics[key] = ci.std
            ci_metrics[key] = {"ci_low": ci.ci_low, "ci_high": ci.ci_high}

        logger.info(f"Cross-validation ({k}-fold) اكتمل: task={task}")
        return {
            "task": task, "k": k, "n": n, "stratified": stratify,
            "per_fold": per_fold,
            "mean_metrics": mean_metrics,
            "std_metrics": std_metrics,
            "ci_metrics": ci_metrics,
        }

    def compare_models(
        self, records: List[Dict[str, Any]],
        factories: Dict[str, Callable], k: int = 5,
        stratify: bool = False, stratify_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """مقارنة عدة نماذج وترتيبها حسب المقياس الرئيسي"""
        if not factories:
            raise ValueError("factories فارغة")
        results = {
            name: self.cross_validate(records, fac, k, stratify, stratify_key)
            for name, fac in factories.items()
        }
        any_task = next(iter(results.values())).get("task")
        primary = "accuracy" if any_task == "classification" else "mae"
        higher_better = any_task == "classification"

        def _score(name):
            return results[name]["mean_metrics"].get(primary, 0.0)

        ranking = sorted(results.keys(), key=_score, reverse=higher_better)
        logger.info(f"ترتيب النماذج ({primary}): {ranking}")
        return {
            "primary_metric": primary,
            "higher_better": higher_better,
            "ranking": ranking,
            "results": results,
                }
