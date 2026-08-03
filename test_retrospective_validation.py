"""
ProtonAI - Test Retrospective Validation
اختبارات التحقق الاستعادي (دقة + ثنائي + معايرة + أخطاء + حراس)
"""

import pytest
from retrospective_validation import RetrospectiveValidator, _safe_div


def _r(pred, act, conf=None):
    d = {"predicted": pred, "actual": act}
    if conf is not None:
        d["confidence"] = conf
    return d


# TP=2 FP=1 FN=1 TN=1 → accuracy=0.6
RECORDS = [_r("M", "M"), _r("M", "M"), _r("B", "B"), _r("M", "B"), _r("B", "M")]


@pytest.fixture
def rv():
    return RetrospectiveValidator(positive_label="M", negative_label="B")


class TestSafeDiv:
    def test_normal(self):
        assert _safe_div(1, 2) == 0.5

    def test_zero_denominator(self):
        assert _safe_div(1, 0) == 0.0


class TestAccuracy:
    def test_perfect(self):
        v = RetrospectiveValidator()
        assert v.validate([_r("M", "M"), _r("B", "B")])["accuracy"] == 1.0

    def test_partial(self, rv):
        assert rv.validate(RECORDS)["accuracy"] == pytest.approx(0.6)

    def test_counts(self, rv):
        s = rv.validate(RECORDS)
        assert s["n"] == 5
        assert s["n_correct"] == 3
        assert s["n_errors"] == 2


class TestBinaryMetrics:
    def test_confusion(self, rv):
        c = rv.validate(RECORDS)["confusion"]
        assert c == {"TP": 2, "FP": 1, "FN": 1, "TN": 1}

    def test_sensitivity(self, rv):
        assert rv.validate(RECORDS)["sensitivity"] == pytest.approx(2 / 3)

    def test_specificity(self, rv):
        assert rv.validate(RECORDS)["specificity"] == pytest.approx(0.5)

    def test_ppv(self, rv):
        assert rv.validate(RECORDS)["ppv"] == pytest.approx(2 / 3)

    def test_npv(self, rv):
        assert rv.validate(RECORDS)["npv"] == pytest.approx(0.5)

    def test_no_labels_omits_binary(self):
        v = RetrospectiveValidator()
        s = v.validate(RECORDS)
        assert "sensitivity" not in s
        assert "confusion" not in s


class TestCalibration:
    def test_correct_more_confident(self):
        recs = [_r("M", "M", 0.9), _r("M", "M", 0.8), _r("M", "B", 0.4)]
        cal = RetrospectiveValidator().validate(recs)["calibration"]
        assert cal["confidence_correct"] > cal["confidence_incorrect"]

    def test_mean_confidence(self):
        recs = [_r("M", "M", 0.9), _r("M", "B", 0.5)]
        cal = RetrospectiveValidator().validate(recs)["calibration"]
        assert cal["mean_confidence"] == pytest.approx(0.7)

    def test_no_confidence_omits(self, rv):
        assert "calibration" not in rv.validate(RECORDS)


class TestErrors:
    def test_errors_captured(self, rv):
        errs = rv.validate(RECORDS)["errors"]
        assert len(errs) == 2
        assert {"predicted": "M", "actual": "B"} in errs

    def test_errors_feed_improvement(self, rv):
        # الأخطاء تحمل الحقول اللازمة لحلقة التحسين لاحقاً
        for e in rv.validate(RECORDS)["errors"]:
            assert "predicted" in e and "actual" in e


class TestGuards:
    def test_empty_raises(self, rv):
        with pytest.raises(ValueError):
            rv.validate([])

    def test_missing_key_raises(self, rv):
        with pytest.raises(ValueError):
            rv.validate([{"predicted": "M"}])
