"""
ProtonAI - Test Dataset Contracts
اختبارات عقود البيانات المعتمدة
"""

import pytest
from dataset_contracts import (
    ColumnSpec, DatasetContract, UCI_CANCER, get_contract,
)


def _uci_record(**overrides):
    rec = {
        "diagnosis": "M",
        "radius_mean": 15.0,
        "texture_mean": 20.0,
        "perimeter_mean": 100.0,
        "area_mean": 700.0,
        "smoothness_mean": 0.1,
    }
    rec.update(overrides)
    return rec


class TestColumnSpec:
    def test_valid_dtypes(self):
        for dt in ("float", "int", "str"):
            assert ColumnSpec("x", dtype=dt).dtype == dt

    def test_invalid_dtype_raises(self):
        with pytest.raises(ValueError):
            ColumnSpec("x", dtype="bool")


class TestValidateRecord:
    def test_valid_record_no_issues(self):
        assert UCI_CANCER.validate_record(_uci_record()) == []

    def test_missing_required_column(self):
        rec = _uci_record()
        del rec["diagnosis"]
        issues = UCI_CANCER.validate_record(rec)
        assert any(i.column == "diagnosis" for i in issues)

    def test_empty_string_is_missing(self):
        issues = UCI_CANCER.validate_record(_uci_record(radius_mean=""))
        assert any(i.column == "radius_mean" for i in issues)

    def test_non_numeric_in_float_column(self):
        issues = UCI_CANCER.validate_record(_uci_record(radius_mean="abc"))
        assert any(i.column == "radius_mean" for i in issues)

    def test_below_min_value(self):
        issues = UCI_CANCER.validate_record(_uci_record(area_mean=-5))
        assert any(i.column == "area_mean" for i in issues)

    def test_above_max_value(self):
        issues = UCI_CANCER.validate_record(_uci_record(smoothness_mean=2.0))
        assert any(i.column == "smoothness_mean" for i in issues)

    def test_disallowed_categorical_value(self):
        issues = UCI_CANCER.validate_record(_uci_record(diagnosis="X"))
        assert any(i.column == "diagnosis" for i in issues)

    def test_allowed_categorical_value(self):
        assert UCI_CANCER.validate_record(_uci_record(diagnosis="B")) == []


class TestIntColumn:
    def test_int_column_rejects_float_value(self):
        contract = DatasetContract("t", [ColumnSpec("n", dtype="int")])
        issues = contract.validate_record({"n": 3.5})
        assert any(i.column == "n" for i in issues)

    def test_int_column_accepts_whole_number(self):
        contract = DatasetContract("t", [ColumnSpec("n", dtype="int")])
        assert contract.validate_record({"n": 3}) == []

    def test_optional_column_missing_ok(self):
        contract = DatasetContract("t", [ColumnSpec("n", dtype="float", required=False)])
        assert contract.validate_record({}) == []


class TestValidateDataset:
    def test_all_valid(self):
        records = [_uci_record(), _uci_record(diagnosis="B")]
        report = UCI_CANCER.validate_dataset(records)
        assert report.total == 2
        assert report.valid_count == 2
        assert report.invalid_count == 0
        assert report.is_acceptable is True

    def test_mixed_valid_invalid(self):
        records = [_uci_record(), _uci_record(diagnosis="X"), _uci_record(area_mean=-1)]
        report = UCI_CANCER.validate_dataset(records)
        assert report.valid_count == 1
        assert report.invalid_count == 2
        assert len(report.invalid_details) == 2

    def test_acceptance_threshold(self):
        records = [_uci_record()] * 9 + [_uci_record(diagnosis="X")]
        report = UCI_CANCER.validate_dataset(records, acceptance_threshold=0.95)
        assert report.is_acceptable is False  # 90% < 95%
        report2 = UCI_CANCER.validate_dataset(records, acceptance_threshold=0.80)
        assert report2.is_acceptable is True  # 90% >= 80%

    def test_summary_keys(self):
        report = UCI_CANCER.validate_dataset([_uci_record()])
        assert set(report.summary().keys()) == {
            "total", "valid_count", "invalid_count", "acceptance_rate", "is_acceptable"
        }

    def test_empty_dataset(self):
        report = UCI_CANCER.validate_dataset([])
        assert report.total == 0
        assert report.acceptance_rate == 0.0


class TestRegistry:
    def test_get_known_contract(self):
        assert get_contract("uci_cancer").name == "UCI Breast Cancer Wisconsin"

    def test_get_unknown_raises(self):
        with pytest.raises(KeyError):
            get_contract("nonexistent")

    def test_required_columns(self):
        req = UCI_CANCER.required_columns()
        assert "diagnosis" in req
        assert "radius_mean" in req
