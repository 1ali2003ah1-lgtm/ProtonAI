"""
ProtonAI - Test Strict Validation
اختبارات طبقة التحقق الصارم
"""

import pytest
from strict_validation import (
    StrictValidator, Severity, detect_outliers_iqr, _percentile,
)


def _good():
    return {"patient_id": "P1", "age": 50, "gender": "M", "tumor_type": "lung"}


class TestCompleteness:
    def test_complete_record_no_errors(self):
        r = StrictValidator().validate_record(_good(), mode="lenient")
        assert r.errors() == []

    def test_missing_required_is_error(self):
        rec = _good()
        del rec["gender"]
        r = StrictValidator().validate_record(rec)
        assert len(r.errors()) == 1
        assert r.errors()[0].field == "gender"
        assert r.is_valid is False

    def test_empty_string_required_is_error(self):
        rec = _good()
        rec["patient_id"] = "   "
        r = StrictValidator().validate_record(rec)
        assert any(i.field == "patient_id" for i in r.errors())


class TestTypes:
    def test_wrong_type_is_error(self):
        rec = _good()
        rec["age"] = "not_a_number"
        r = StrictValidator().validate_record(rec)
        assert any(i.field == "age" for i in r.errors())

    def test_numeric_string_age_accepted(self):
        rec = _good()
        rec["age"] = "50"  # نص رقمي من CSV → متسامح
        r = StrictValidator().validate_record(rec, mode="lenient")
        assert not any(i.field == "age" and i.severity == Severity.ERROR for i in r.issues)


class TestHardRanges:
    def test_age_over_absolute_limit_is_error(self):
        rec = _good()
        rec["age"] = 200
        r = StrictValidator().validate_record(rec)
        assert any(i.field == "age" for i in r.errors())

    def test_dose_within_limit_ok(self):
        rec = _good()
        rec["dose_gy"] = 70.0
        r = StrictValidator().validate_record(rec, mode="lenient")
        assert not any(i.field == "dose_gy" for i in r.errors())

    def test_dose_over_physical_limit_is_error(self):
        rec = _good()
        rec["dose_gy"] = 300.0
        r = StrictValidator().validate_record(rec)
        assert any(i.field == "dose_gy" for i in r.errors())


class TestOutliers:
    def test_percentile_basic(self):
        assert _percentile([1.0, 2.0, 3.0], 0.5) == 2.0

    def test_detect_outlier(self):
        vals = [10, 11, 12, 13, 14, 100]
        out = detect_outliers_iqr(vals)
        assert 100 in out

    def test_no_outlier_in_uniform(self):
        out = detect_outliers_iqr([10, 11, 12, 13, 14])
        assert out == []

    def test_small_batch_no_detection(self):
        assert detect_outliers_iqr([1, 100]) == []

    def test_outlier_is_warning_not_error(self):
        records = [{"age": v} for v in [50, 51, 52, 53, 54, 200]]
        r = StrictValidator().validate_batch_outliers(records, ["age"], mode="lenient")
        assert len(r.warnings()) >= 1
        assert len(r.errors()) == 0
        assert r.is_valid is True  # بالـ lenient التحذير ما يرفض

    def test_outlier_rejects_in_strict(self):
        records = [{"age": v} for v in [50, 51, 52, 53, 54, 200]]
        r = StrictValidator().validate_batch_outliers(records, ["age"], mode="strict")
        assert r.is_valid is False  # بالـ strict التحذير يرفض


class TestReport:
    def test_summary_keys(self):
        r = StrictValidator().validate_record(_good())
        s = r.summary()
        assert set(s.keys()) == {"valid", "mode", "errors", "warnings"}

    def test_strict_mode_stricter_than_lenient(self):
        records = [{"age": v} for v in [50, 51, 52, 53, 54, 200]]
        v = StrictValidator()
        strict = v.validate_batch_outliers(records, ["age"], mode="strict")
        lenient = v.validate_batch_outliers(records, ["age"], mode="lenient")
        assert strict.is_valid is False
        assert lenient.is_valid is True
