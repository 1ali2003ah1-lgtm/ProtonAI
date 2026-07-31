"""
ProtonAI - Hyperparameter Tuner
ضبط معاملات النموذج ذاتياً (grid / random search) مع تقييم على بيانات محجوزة
يقارن النتيجة بالافتراضي ويربط البحث ببصمة تقسيم ثابتة
"""

import itertools
import random as _random
import logging
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

from generic_model import GenericModel
from experiment_tracker import stable_split

logger = logging.getLogger("ProtonAI.HyperparameterTuner")

# المعاملات التي يقبلها GenericModel (أي مفتاح خارجها يُرفض صراحة)
KNOWN_PARAMS = {"n_estimators", "random_seed", "missing_strategy", "task"}


@dataclass
class TuningResult:
    """نتيجة بحث المعاملات"""
    best_config: Dict[str, Any]
    best_score: float
    baseline_config: Dict[str, Any]
    baseline_score: float
    improvement: float
    all_results: List[Dict[str, Any]]
    n_trials: int
    strategy: str
    metric_name: str
    higher_better: bool = True
    split_fingerprint: str = ""
    train_samples: int = 0
    val_samples: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class HyperparameterTuner:
    """
    باحث المعاملات.
    - strategy="grid": كل التوليفات. "random": n_iter توليفة عشوائية حتمية.
    - search: يدرّب كل config على train ويقيّم على val (محجوزة)، يرجع TuningResult.
    - baseline = الإعدادات الافتراضية (config فارغ) لقياس التحسين.
    """

    def __init__(
        self,
        feature_columns: List[str],
        target_column: str,
        param_grid: Dict[str, List[Any]],
        strategy: str = "grid",
        n_iter: int = 10,
        seed: int = 42,
        val_ratio: float = 0.2,
        task: str = "auto",
    ):
        if strategy not in ("grid", "random"):
            raise ValueError("strategy يجب أن يكون grid أو random")
        if not (0 < val_ratio < 1):
            raise ValueError("val_ratio يجب أن يكون بين 0 و 1 (حصراً)")
        if n_iter < 1:
            raise ValueError("n_iter يجب أن يكون >= 1")
        if not param_grid:
            raise ValueError("param_grid لا يمكن أن يكون فارغاً")
        for k, v in param_grid.items():
            if k not in KNOWN_PARAMS:
                raise ValueError(f"معامل غير معروف: {k}. المسموح: {sorted(KNOWN_PARAMS)}")
            if not isinstance(v, list) or not v:
                raise ValueError(f"قيمة {k} يجب أن تكون قائمة غير فارغة")
        self.feature_columns = list(feature_columns)
        self.target_column = target_column
        self.param_grid = {k: list(v) for k, v in param_grid.items()}
        self.strategy = strategy
        self.n_iter = n_iter
        self.seed = seed
        self.val_ratio = val_ratio
        self.task = task

    def _all_combos(self) -> List[Dict[str, Any]]:
        """كل توليفات الـ grid (مفاتيح مرتبة → حتمية)"""
        keys = sorted(self.param_grid.keys())
        lists = [self.param_grid[k] for k in keys]
        return [dict(zip(keys, combo)) for combo in itertools.product(*lists)]

    def _configs(self) -> List[Dict[str, Any]]:
        """التوليفات حسب الاستراتيجية"""
        combos = self._all_combos()
        if self.strategy == "grid":
            return combos
        rng = _random.Random(self.seed)
        k = min(self.n_iter, len(combos))
        return rng.sample(combos, k)

    def _build(self, config: Dict[str, Any]) -> GenericModel:
        """بناء نموذج بمعاملات مضبوطة (بذرة ثابتة افتراضياً للتكرار)"""
        kwargs: Dict[str, Any] = {
            "feature_columns": self.feature_columns,
            "target_column": self.target_column,
            "task": self.task,
            "random_seed": self.seed,
        }
        for k, v in config.items():
            if k in KNOWN_PARAMS:
                kwargs[k] = v
        return GenericModel(**kwargs)

    def _score(self, model: GenericModel, train: List[Dict], val: List[Dict]):
        """تدريب على train وتقييم على val، يرجع (score, metric_name) موحد higher-better"""
        model.fit(train)
        ev = model.evaluate(val)
        if model.task_ == "classification":
            return float(ev["accuracy"]), "accuracy"
        return -float(ev["mae"]), "neg_mae"

    def search(self, records: List[Dict[str, Any]]) -> TuningResult:
        """تنفيذ البحث، يرجع TuningResult شاملاً"""
        if not records:
            raise ValueError("records فارغة")
        train, val, fp = stable_split(records, 1.0 - self.val_ratio, self.seed)
        if not val:
            val = list(train)

        baseline = self._build({})
        base_score, metric_name = self._score(baseline, train, val)

        results: List[Dict[str, Any]] = []
        for cfg in self._configs():
            model = self._build(cfg)
            score, metric_name = self._score(model, train, val)
            results.append({"config": cfg, "score": score})

        best = max(results, key=lambda r: r["score"])
        improvement = best["score"] - base_score
        logger.info(f"Tuning ({self.strategy}) اكتمل: best_score={best['score']:.4f}, "
                    f"improvement={improvement:+.4f}")
        return TuningResult(
            best_config=best["config"], best_score=best["score"],
            baseline_config={}, baseline_score=base_score,
            improvement=improvement, all_results=results,
            n_trials=len(results), strategy=self.strategy,
            metric_name=metric_name, higher_better=True,
            split_fingerprint=fp, train_samples=len(train), val_samples=len(val),
      )
