"""
ProtonAI - Stage-4 AI Runner
المايسترو النهائي: يربط كل وحدات المرحلة 4 بتقرير واحد قابل للتكرار
ensemble (منتج) ← registry ← tracker ← link/verify ← explain ← dose ← compare
"""

import tempfile
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from generic_model import GenericModel
from ensemble_model import EnsembleModel
from ai_model_compare import AIModelComparer
from explainability import Explainability
from dose_engine import DoseEngine
from model_registry import ModelRegistry
from versioned_model_link import VersionedModelLink
from experiment_tracker import ExperimentTracker, stable_split, fingerprint
from scientific_report import ScientificReport
from run_uci_training import UCI_FEATURES, UCI_TARGET

logger = logging.getLogger("ProtonAI.AIStage4")


def run_ai_analysis(
    records: List[Dict[str, Any]],
    output_dir: Optional[str | Path] = None,
    feature_columns: Optional[List[str]] = None,
    target_column: Optional[str] = None,
    task: str = "auto",
    seed: int = 42,
    train_ratio: float = 0.8,
    ensemble_configs: Optional[List[Dict[str, Any]]] = None,
    tuner_grid: Optional[Dict[str, List[Any]]] = None,
    tumor_type_key: str = "tumor_type",
    protocols: Optional[Dict[str, tuple]] = None,
    top_k: int = 3,
    registry: Optional[ModelRegistry] = None,
    tracker: Optional[ExperimentTracker] = None,
    audit: Any = None,
    name: str = "protonai_model",
) -> Dict[str, Any]:
    """
    تشغيل تحليل المرحلة 4 الكامل، يرجع قاموساً شاملاً + يحفظ التقارير إن طُلب.
    """
    if not records:
        raise ValueError("records فارغة")
    feature_columns = list(feature_columns) if feature_columns else list(UCI_FEATURES)
    target_column = target_column or UCI_TARGET

    # 1) تقسيم ثابت + بصمة بيانات التدريب
    train, test, split_fp = stable_split(records, train_ratio, seed)
    if not test:
        test = list(train)
    data_fp = fingerprint(train)

    # 2) المنتج: ensemble مدرّب على train
    ens = EnsembleModel(feature_columns, target_column,
                        configs=ensemble_configs, task=task, seed=seed)
    ens.fit(train)
    ens_eval = ens.evaluate(test)
    task_resolved = ens.task_
    rep = ens.models[0]  # ممثّل شجري للتفسير/الدوز/عدم اليقين

    # 3) الإثبات: مقارنة single/tuned/ensemble على نفس التقسيم
    comparer = AIModelComparer(
        feature_columns, target_column, task=task, seed=seed,
        train_ratio=train_ratio, ensemble_configs=ensemble_configs,
        tuner_grid=tuner_grid)
    comp = comparer.compare(records)

    # 4) التجربة القابلة للتكرار
    tracker = tracker if tracker is not None else ExperimentTracker()
    exp = tracker.register(
        name, {"features": feature_columns, "target": target_column,
               "seed": seed, "train_ratio": train_ratio,
               "ensemble_configs": ensemble_configs},
        train, metrics=ens_eval, split_fingerprint=split_fp, seed=seed)

    # 5) المكتبة (dependency injection أو إنشاء تلقائي)
    if registry is None:
        store = (Path(output_dir) / "registry") if output_dir else Path(tempfile.mkdtemp())
        registry = ModelRegistry(store, audit=audit)
    entry = registry.register(
        name, ens, metrics=ens_eval, data_fingerprint=data_fp,
        experiment_id=exp.experiment_id,
        tags=["ensemble", task_resolved], notes="Stage-4 AI product")

    # 6) الربط + التحقق + سلسلة النسب
    link = VersionedModelLink(registry, tracker)
    link_rec = link.link(entry.model_id, experiment_id=exp.experiment_id, data=train)
    ver = link.verify(entry.model_id, data=train, split_fp=split_fp,
                      experiment_id=exp.experiment_id)
    lin = link.lineage(entry.model_id)

    # 7) التفسير (عينة من test)
    sample = test[0]
    explainer = Explainability(seed=seed)
    local = explainer.local_explanation(rep, sample)
    top = explainer.top_features(rep, k=top_k)

    # 8) محرك الجرعة السريري
    engine = DoseEngine(rep, tumor_type_key=tumor_type_key,
                        protocols=protocols, top_k=top_k, seed=seed)
    dose = engine.recommend(sample)

    # 9) التقرير العلمي
    report = ScientificReport(
        title="ProtonAI Stage-4 AI Report", dataset_name="UCI / custom")
    report.add_section("Model Comparison", {"type": "raw", "data": {
        "ranking": comp["ranking"], "best_name": comp["best_name"],
        "primary_metric": comp["primary_metric"], "values": comp["values"],
        "improvements": comp["improvements"], "beats_single": comp["beats_single"]}})
    report.add_section("Reproducibility", {"type": "raw", "data": {
        "data_fingerprint": data_fp, "split_fingerprint": split_fp,
        "experiment_id": exp.experiment_id, "model_id": entry.model_id,
        "version": entry.version, "verified": link_rec.verified,
        "verification_valid": ver["valid"]}})
    report.add_section("Explanation", {"type": "raw", "data": {
        "predicted": local["predicted"], "top_features": top,
        "class_probabilities": local.get("class_probabilities")}})
    report.add_section("Dose Engine", {"type": "raw", "data": dose})
    report.add_section("Registry", {"type": "raw", "data": registry.summary()})

    result = {
        "task": task_resolved, "train": len(train), "test": len(test),
        "comparison": comp,
        "reproducibility": {
            "data_fingerprint": data_fp, "split_fingerprint": split_fp,
            "experiment_id": exp.experiment_id, "model_id": entry.model_id,
            "version": entry.version, "verified": link_rec.verified},
        "verification": ver, "lineage": lin,
        "explanation": {"local": local, "top_features": top},
        "dose": dose, "registry_summary": registry.summary(),
        "report_markdown": report.to_markdown(),
    }

    if output_dir:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        report.save_markdown(out / "ai_report.md")
        report.save_json(out / "ai_report.json")
        registry.save(out / "registry.json")
        tracker.save(out / "experiments.json")
        ens.save(out / "ensemble_product.pkl")
        logger.info(f"تم حفظ تحليل المرحلة 4 في: {out}")

    return result
