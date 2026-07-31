"""
ProtonAI - Scientific UCI Analysis
التحليل العلمي الكامل: يربط كل وحدات المرحلة 3 بتقرير واحد قابل للتكرار
تقسيم ثابت ← تدريب ← تقييم ← عدم يقين ← أخطاء ← baselines ← مراجعة ← تدقيق
"""

import csv
import io
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from generic_model import GenericModel
from scientific_evaluator import ScientificEvaluator
from scientific_report import ScientificReport
from experiment_tracker import ExperimentTracker, stable_split, fingerprint
from uncertainty import UncertaintyEstimator
from error_analysis import ErrorAnalyzer
from benchmark import BenchmarkEvaluator
from physician_review import PhysicianReviewLoop
from run_uci_training import UCI_FEATURES, UCI_TARGET

logger = logging.getLogger("ProtonAI.ScientificUCI")


def _miss(value: Any) -> bool:
    """هل القيمة مفقودة؟"""
    return value is None or str(value).strip() == ""


def _clean(records: List[Dict[str, Any]], features: List[str], target: str) -> List[Dict[str, Any]]:
    """إسقاط السجلات الناقصة الميزات أو الهدف (يضمن تطابق الأطوال)"""
    out = []
    for r in records:
        if any(_miss(r.get(f)) for f in features) or _miss(r.get(target)):
            continue
        out.append(r)
    return out


def run_scientific_analysis(
    records: List[Dict[str, Any]],
    output_dir: Optional[str | Path] = None,
    train_ratio: float = 0.8,
    seed: int = 42,
    feature_columns: Optional[List[str]] = None,
    target_column: Optional[str] = None,
    k: int = 3,
    low_confidence_threshold: float = 0.7,
    high_ci_width: Optional[float] = None,
    clinical_tolerance: float = 3.0,
    run_cv: bool = True,
) -> Dict[str, Any]:
    """
    تشغيل التحليل العلمي الكامل، يرجع قاموساً شاملاً + يحفظ التقارير إن طُلب.
    """
    feature_columns = list(feature_columns) if feature_columns else list(UCI_FEATURES)
    target_column = target_column or UCI_TARGET
    clean = _clean(records, feature_columns, target_column)
    if len(clean) < 4:
        raise ValueError("البيانات الصالحة أقل من 4 سجلات")

    # 1) تقسيم ثابت ببصمة
    train, test, split_fp = stable_split(clean, train_ratio, seed)
    if not test:
        test = list(train)

    # 2) تدريب
    model = GenericModel(feature_columns, target_column, random_seed=seed)
    model.fit(train)
    task = model.task_

    # 3) تنبؤ + تقييم
    y_pred = model.predict(test)
    evaluator = ScientificEvaluator(random_seed=seed)
    unc_est = UncertaintyEstimator()
    analyzer = ErrorAnalyzer(tolerance=clinical_tolerance)
    bench = BenchmarkEvaluator()

    if task == "classification":
        y_true = [str(r[target_column]) for r in test]
        eval_res = evaluator.evaluate_classification(y_true, y_pred)
        per_unc = unc_est.classification_uncertainty(model, test)
        agg_unc = unc_est.aggregate_classification(per_unc, low_confidence_threshold)
        err = analyzer.analyze_classification(
            y_true, y_pred, records=test,
            per_sample=[{"confidence": u["confidence"]} for u in per_unc],
            feature_keys=feature_columns)
        y_train = [str(r[target_column]) for r in train]
        baselines = bench.classification_baselines(y_train, y_true)
        verdict = bench.verdict({"accuracy": eval_res["accuracy"]}, baselines, "classification")
        skills = {n: bench.classification_skill(eval_res["accuracy"], a) for n, a in baselines.items()}
        correlate = None
        abs_err = None
    else:
        y_true = [float(r[target_column]) for r in test]
        eval_res = evaluator.evaluate_regression(y_true, y_pred, clinical_tolerance)
        per_unc = [{**u, "ci_width": u["ci_high"] - u["ci_low"]}
                   for u in unc_est.regression_uncertainty(model, test)]
        agg_unc = unc_est.aggregate_regression(
            per_unc, high_ci_width if high_ci_width else clinical_tolerance * 2)
        abs_err = [abs(p - t) for p, t in zip(y_pred, y_true)]
        err = analyzer.analyze_regression(
            y_true, y_pred, records=test,
            per_sample=[{"ci_width": u["ci_width"]} for u in per_unc],
            feature_keys=feature_columns)
        y_train = [float(r[target_column]) for r in train]
        baselines = bench.regression_baselines(y_train, y_true)
        model_mse = eval_res["rmse"] ** 2
        verdict = bench.verdict({"mae": eval_res["mae"]}, baselines, "regression")
        skills = {n: bench.regression_skill(model_mse, b["mse"]) for n, b in baselines.items()}
        correlate = analyzer.correlate_with_uncertainty(abs_err, [u["std"] for u in per_unc])

    # 4) حلقة مراجعة الطبيب
    loop = PhysicianReviewLoop(
        low_confidence_threshold=low_confidence_threshold,
        high_ci_width=high_ci_width, clinical_tolerance=clinical_tolerance)
    for i, r in enumerate(test):
        if task == "classification":
            loop.flag_for_review(r.get("id", i), y_pred[i], true_value=y_true[i],
                                 confidence=per_unc[i]["confidence"], record=r)
        else:
            loop.flag_for_review(r.get("id", i), y_pred[i], true_value=y_true[i],
                                 ci_width=per_unc[i]["ci_width"], abs_error=abs_err[i], record=r)

    # 5) تسجيل التجربة (reproducibility)
    primary = "accuracy" if task == "classification" else "mae"
    tracker = ExperimentTracker()
    exp = tracker.register(
        name="uci_scientific",
        config={"features": feature_columns, "target": target_column,
                "seed": seed, "train_ratio": train_ratio, "k": k},
        data=clean, metrics={primary: eval_res[primary]},
        split_fingerprint=split_fp, seed=seed,
        notes=f"task={task}; beats_all={verdict['beats_all_baselines']}")

    # 6) cross-validation (اختياري)
    cv_res = None
    if run_cv and len(train) >= k:
        cv_res = evaluator.cross_validate(
            train, lambda: GenericModel(feature_columns, target_column, random_seed=seed),
            k=k, stratify=(task == "classification"),
            stratify_key=(target_column if task == "classification" else None))

    # 7) التقرير العلمي
    report = ScientificReport(
        title="ProtonAI Scientific Analysis", dataset_name="UCI Breast Cancer")
    report.add_section("Reproducibility", {"type": "raw", "data": {
        "data_fingerprint": fingerprint(clean), "split_fingerprint": split_fp,
        "experiment_id": exp.experiment_id, "seed": seed,
        "train": len(train), "test": len(test)}})
    report.add_metrics(eval_res, name="Evaluation Metrics")
    if cv_res:
        report.add_cross_validation(cv_res, name="Cross-Validation")
    report.add_section("Uncertainty", {"type": "raw", "data": {**agg_unc, "task": task}})
    report.add_section("Error Analysis", {"type": "raw", "data": err})
    report.add_section("Benchmark", {"type": "raw", "data": {
        "verdict": verdict, "skills": skills, "baselines": baselines}})
    if correlate:
        report.add_section("Calibration", {"type": "raw", "data": correlate})
    report.add_section("Physician Review", {"type": "raw", "data": loop.stats()})

    result = {
        "task": task, "train": len(train), "test": len(test),
        "evaluation": eval_res, "uncertainty": agg_unc, "error": err,
        "benchmark": {"verdict": verdict, "skills": skills, "baselines": baselines},
        "physician_review": loop.stats(), "calibration": correlate,
        "reproducibility": {"data_fingerprint": fingerprint(clean),
                            "split_fingerprint": split_fp,
                            "experiment_id": exp.experiment_id, "seed": seed},
        "cross_validation": cv_res, "report_markdown": report.to_markdown(),
    }

    if output_dir:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        report.save_markdown(out / "scientific_report.md")
        report.save_json(out / "scientific_report.json")
        tracker.save(out / "experiments.json")
        loop.save(out / "physician_review.json")
        logger.info(f"تم حفظ التحليل العلمي في: {out}")

    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    path = sys.argv[1] if len(sys.argv) > 1 else "data/uci_cancer.csv"
    with open(path, encoding="utf-8") as f:
        recs = list(csv.DictReader(f))
    res = run_scientific_analysis(recs, output_dir="scientific_output")
    print("النوع:", res["task"])
    print("يتغلب على كل الـ baselines:", res["benchmark"]["verdict"]["beats_all_baselines"])
    print("محال للمراجعة:", res["physician_review"]["total_flagged"])
