"""
ProtonAI - AI Model Compare
مقارنة عادلة: single vs tuned vs ensemble على نفس التقسيم الثابت
تثبت بالأرقام إن الضبط والتجميع يحسّنان الأداء (جدول جاهز للورقة)
"""

import logging
from typing import List, Dict, Any, Optional

from generic_model import GenericModel
from scientific_evaluator import ScientificEvaluator
from hyperparameter_tuner import HyperparameterTuner
from ensemble_model import EnsembleModel
from experiment_tracker import stable_split

logger = logging.getLogger("ProtonAI.AIModelCompare")

# أسماء النماذج بالجدول (ثابتة)
NAME_SINGLE = "single"
NAME_TUNED = "tuned"
NAME_ENSEMBLE = "ensemble"

DEFAULT_TUNER_GRID = {"n_estimators": [10, 30, 60]}


class AIModelComparer:
    """
    مقارن النماذج.
    - compare: يبني single/tuned/ensemble، يدرّبهم على نفس train، يقيّمهم على نفس test.
    - يرجع جدولاً + ترتيباً + تحسينات + verdict (beats_single).
    """

    def __init__(
        self,
        feature_columns: List[str],
        target_column: str,
        task: str = "auto",
        seed: int = 42,
        train_ratio: float = 0.8,
        ensemble_configs: Optional[List[Dict[str, Any]]] = None,
        tuner_grid: Optional[Dict[str, List[Any]]] = None,
        tuner_strategy: str = "grid",
    ):
        if not feature_columns:
            raise ValueError("feature_columns لا يمكن أن تكون فارغة")
        if not (0 < train_ratio < 1):
            raise ValueError("train_ratio يجب أن يكون بين 0 و 1 (حصراً)")
        if ensemble_configs is not None and not ensemble_configs:
            raise ValueError("ensemble_configs إن مُرّرت يجب أن تكون غير فارغة")
        if tuner_grid is not None and not tuner_grid:
            raise ValueError("tuner_grid إن مُرّر يجب أن يكون غير فارغ")
        self.feature_columns = list(feature_columns)
        self.target_column = target_column
        self.task = task
        self.seed = seed
        self.train_ratio = train_ratio
        self.ensemble_configs = ensemble_configs
        self.tuner_grid = dict(tuner_grid) if tuner_grid else dict(DEFAULT_TUNER_GRID)
        self.tuner_strategy = tuner_strategy

    def _build_single(self) -> GenericModel:
        """نموذج مفرد بإعدادات افتراضية"""
        return GenericModel(self.feature_columns, self.target_column,
                            task=self.task, random_seed=self.seed)

    def _build_with_config(self, config: Dict[str, Any]) -> GenericModel:
        """نموذج بمعاملات مضبوطة (بذرة ثابتة افتراضياً)"""
        kwargs: Dict[str, Any] = {
            "feature_columns": self.feature_columns,
            "target_column": self.target_column,
            "task": self.task, "random_seed": self.seed,
        }
        for k in ("n_estimators", "random_seed", "missing_strategy", "task"):
            if k in config:
                kwargs[k] = config[k]
        return GenericModel(**kwargs)

    def _eval(self, evaluator: ScientificEvaluator, model: Any, test: List[Dict]) -> Dict[str, Any]:
        """تقييم نموذج GenericModel على test"""
        y_pred = model.predict(test)
        if model.task_ == "classification":
            y_true = [str(r[self.target_column]) for r in test]
            return evaluator.evaluate_classification(y_true, y_pred)
        y_true = [float(r[self.target_column]) for r in test]
        return evaluator.evaluate_regression(y_true, y_pred)

    def _eval_ensemble(self, evaluator: ScientificEvaluator, ens: EnsembleModel, test: List[Dict]) -> Dict[str, Any]:
        """تقييم ensemble على test"""
        y_pred = ens.predict(test)
        if ens.task_ == "classification":
            y_true = [str(r[self.target_column]) for r in test]
            return evaluator.evaluate_classification(y_true, y_pred)
        y_true = [float(r[self.target_column]) for r in test]
        return evaluator.evaluate_regression(y_true, y_pred)

    @staticmethod
    def _primary(ev: Dict[str, Any]):
        """استخراج المقياس الرئيسي + اتجاهه"""
        if ev["task"] == "classification":
            return ev["accuracy"], "accuracy", True
        return ev["mae"], "mae", False

    def compare(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """المقارنة الكاملة، ترجع جدولاً + verdict"""
        if not records:
            raise ValueError("records فارغة")
        train, test, fp = stable_split(records, self.train_ratio, self.seed)
        if not test:
            test = list(train)
        evaluator = ScientificEvaluator(random_seed=self.seed)

        # 1) single
        single = self._build_single()
        single.fit(train)
        task = single.task_
        single_eval = self._eval(evaluator, single, test)

        # 2) tuned (بحث داخل train، ثم تدريب نهائي على نفس train)
        tuner = HyperparameterTuner(
            self.feature_columns, self.target_column, self.tuner_grid,
            strategy=self.tuner_strategy, seed=self.seed, task=self.task)
        tune_res = tuner.search(train)
        tuned = self._build_with_config(tune_res.best_config)
        tuned.fit(train)
        tuned_eval = self._eval(evaluator, tuned, test)

        # 3) ensemble
        ens = EnsembleModel(
            self.feature_columns, self.target_column,
            configs=self.ensemble_configs, task=self.task, seed=self.seed)
        ens.fit(train)
        ens_eval = self._eval_ensemble(evaluator, ens, test)
        # إثراء الجدول بعدد نماذج الـ ensemble (شفافية للتقرير النهائي)
        ens_eval["n_models"] = len(ens.models)

        # تجميع الجدول
        higher_better = (task == "classification")
        primary_metric = "accuracy" if higher_better else "mae"
        entries = [(NAME_SINGLE, single_eval), (NAME_TUNED, tuned_eval), (NAME_ENSEMBLE, ens_eval)]
        table = []
        for name, ev in entries:
            val, _, _ = self._primary(ev)
            table.append({"name": name, "task": ev["task"],
                          "primary_metric": primary_metric,
                          "primary_value": val, "metrics": ev})

        vals = {e["name"]: e["primary_value"] for e in table}
        ranked = sorted(table, key=lambda e: e["primary_value"], reverse=higher_better)
        ranking = [e["name"] for e in ranked]
        single_value = vals[NAME_SINGLE]

        # التحسينات (موجب = تحسّن دايماً)
        improvements = {}
        for name in (NAME_TUNED, NAME_ENSEMBLE):
            v = vals[name]
            improvements[name] = (v - single_value) if higher_better else (single_value - v)
        beats_single = {name: improvements[name] > 1e-9 for name in improvements}

        logger.info(f"مقارنة ({task}): ranking={ranking}, beats={beats_single}")
        return {
            "task": task, "primary_metric": primary_metric,
            "higher_better": higher_better,
            "train": len(train), "test": len(test), "split_fingerprint": fp,
            "table": table, "ranking": ranking, "best_name": ranking[0],
            "single_value": single_value, "values": vals,
            "improvements": improvements, "beats_single": beats_single,
      }
