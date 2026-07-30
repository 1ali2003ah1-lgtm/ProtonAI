"""
ProtonAI - Test Data Pipeline
اختبارات خط المعالجة الموحد
"""

import pytest
from data_pipeline import PipelineConfig, DataPipeline
from dataset_contracts import DatasetContract, ColumnSpec
from audit import AuditTrail


def _write_class_csv(path, n=60):
    """بيانات تصنيف بنمط واضح: f1>40 → M وإلا B"""
    lines = ["f1,f2,label"]
    for i in range(n):
        v = 10 + i
        label = "M" if v > 40 else "B"
        lines.append(f"{v},{v * 2},{label}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


@pytest.fixture
def class_csv(tmp_path):
    return _write_class_csv(tmp_path / "c.csv")


def _contract_ok():
    return DatasetContract("c", [
        ColumnSpec("f1", dtype="float", min_value=0),
        ColumnSpec("f2", dtype="float", min_value=0),
        ColumnSpec("label", dtype="str", allowed_values=["M", "B"]),
    ])


class TestRunSuccess:
    def test_success_classification(self, class_csv):
        cfg = PipelineConfig(["f1", "f2"], "label", train_ratio=1.0)
        report = DataPipeline(cfg).run(class_csv)
        assert report.status == "success"
        assert report.succeeded is True
        assert report.evaluation["task"] == "classification"
        assert report.evaluation["accuracy"] >= 0.9

    def test_report_summary_keys(self, class_csv):
        cfg = PipelineConfig(["f1", "f2"], "label", train_ratio=1.0)
        report = DataPipeline(cfg).run(class_csv)
        s = report.summary()
        assert {"status", "loaded", "train_samples", "evaluation"} <= set(s)


class TestContractGate:
    def test_accepts_valid_data(self, class_csv):
        cfg = PipelineConfig(["f1", "f2"], "label", train_ratio=1.0)
        report = DataPipeline(cfg, contract=_contract_ok()).run(class_csv)
        assert report.status == "success"
        assert report.contract["is_acceptable"] is True

    def test_rejects_when_contract_fails(self, class_csv):
        strict = DatasetContract("strict", [ColumnSpec("nonexistent_col", dtype="float")])
        cfg = PipelineConfig(["f1", "f2"], "label", train_ratio=1.0)
        report = DataPipeline(cfg, contract=strict).run(class_csv)
        assert report.status == "rejected"
        assert report.contract["is_acceptable"] is False
        assert report.training is None  # ما درّب لأن البيانات رُفضت


class TestAnonymization:
    def test_anonymize_hashes_ids(self, tmp_path):
        f = tmp_path / "p.csv"
        lines = ["patient_id,age,f1,f2,label"]
        for i in range(40):
            v = 10 + i
            label = "M" if v > 30 else "B"
            lines.append(f"P{i},{20 + i},{v},{v * 2},{label}")
        f.write_text("\n".join(lines) + "\n", encoding="utf-8")

        cfg = PipelineConfig(["f1", "f2"], "label", train_ratio=1.0, anonymize=True)
        report = DataPipeline(cfg).run(f)
        assert report.status == "success"
        assert report.anonymization is not None
        assert report.anonymization["ids_hashed"] == 40


class TestSplit:
    def test_splits_data(self, class_csv):
        cfg = PipelineConfig(["f1", "f2"], "label", train_ratio=0.75, random_seed=42)
        report = DataPipeline(cfg).run(class_csv)
        assert report.status == "success"
        assert report.train_samples == 45
        assert report.test_samples == 15
        assert report.train_samples + report.test_samples == report.loaded

    def test_no_split_when_ratio_one(self, class_csv):
        cfg = PipelineConfig(["f1", "f2"], "label", train_ratio=1.0)
        report = DataPipeline(cfg).run(class_csv)
        assert report.test_samples == 0
        assert report.train_samples == report.loaded


class TestAudit:
    def test_audit_trail_recorded(self, class_csv):
        audit = AuditTrail()
        cfg = PipelineConfig(["f1", "f2"], "label", train_ratio=1.0)
        DataPipeline(cfg, audit=audit).run(class_csv)
        actions = [e.action for e in audit.events]
        assert "load" in actions
        assert "train" in actions
        assert "evaluate" in actions
        assert audit.verify_chain() is True


class TestFailures:
    def test_missing_file_failed(self, tmp_path):
        cfg = PipelineConfig(["f1"], "label")
        report = DataPipeline(cfg).run(tmp_path / "nope.csv")
        assert report.status == "failed"
        assert report.message  # فيه سبب

    def test_invalid_config_raises(self):
        with pytest.raises(ValueError):
            PipelineConfig([], "label")

    def test_invalid_train_ratio_raises(self):
        with pytest.raises(ValueError):
            PipelineConfig(["f1"], "label", train_ratio=1.5)
