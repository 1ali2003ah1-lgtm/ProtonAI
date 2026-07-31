"""
ProtonAI - Test Error Analysis
اختبارات تحليل الأخطاء
"""

import pytest
from error_analysis import ErrorAnalyzer, _pearson, _bin_index


class TestHelpers:
    def test_pearson_perfect_positive(self):
        assert abs(_pearson([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) - 1.0) < 1e-9

    def test_pearson_constant_zero(self):
        assert _pearson([5.0, 5.0, 5.0], [1.0, 2.0, 3.0]) == 0.0

    def test_pearson_single_zero(self):
        assert _pearson([1.0], [2.0]) == 0.0

    def test_bin_index_range(self):
        assert _bin_index(0.0, 0.0, 9.0, 3) == 0
        assert _bin_index(9.0, 0.0, 9.0, 3) == 2  # الحد الأعلى يُكبّح
        assert _bin_index(4.5, 0.0, 9.0, 3) == 1

    def test_bin_index_equal_range(self):
        assert _bin_index(5.0, 5.0, 5.0, 3) == 0


class TestClassification:
    def test_confusion_correct(self):
        a = ErrorAnalyzer()
        res = a.analyze_classification(["M", "B", "M"], ["M", "B", "B"])
        assert res["confusion"]["M"]["M"] == 1
        assert res["confusion"]["M"]["B"] == 1
        assert res["n_errors"] == 1

    def test_accuracy(self):
        a = ErrorAnalyzer()
        res = a.analyze_classification(["M", "B"], ["M", "B"])
        assert res["accuracy"] == 1.0
        assert res["n_errors"] == 0

    def test_per_class_error_rate(self):
        a = ErrorAnalyzer()
        res = a.analyze_classification(["M", "M", "B"], ["M", "B", "B"])
        assert res["per_class_error"]["M"]["error_rate"] == 0.5
        assert res["per_class_error"]["B"]["error_rate"] == 0.0

    def test_worst_cases_overconfident_first(self):
        a = ErrorAnalyzer(top_k=2)
        per = [{}, {"confidence": 0.9}, {}, {"confidence": 0.6}, {}]
        res = a.analyze_classification(
            ["M", "M", "B", "B", "M"], ["M", "B", "B", "M", "M"], per_sample=per)
        assert res["worst_cases"][0]["index"] == 1  # واثق+غلط = الأخطر
        assert res["worst_cases"][0]["confidence"] == 0.9

    def test_borderline_count(self):
        a = ErrorAnalyzer()
        per = [{"confidence": 0.5}, {"confidence": 0.9}, {"confidence": 0.6}]
        res = a.analyze_classification(["M", "B", "M"], ["M", "B", "M"], per_sample=per)
        assert res["borderline_count"] == 2  # 0.5 و 0.6 < 0.7

    def test_feature_keys_in_worst(self):
        a = ErrorAnalyzer()
        records = [{"f1": 10, "extra": "x"}, {"f1": 20, "extra": "y"}]
        res = a.analyze_classification(["M", "B"], ["B", "M"], records=records,
                                       feature_keys=["f1"])
        assert res["worst_cases"][0]["record"] == {"f1": 10}
        assert "extra" not in res["worst_cases"][0]["record"]

    def test_length_mismatch_raises(self):
        with pytest.raises(ValueError):
            ErrorAnalyzer().analyze_classification(["M"], ["M", "B"])


class TestRegression:
    def test_bias_positive_when_overpredicting(self):
        a = ErrorAnalyzer()
        res = a.analyze_regression([1.0, 2.0, 3.0], [2.0, 3.0, 4.0])
        assert abs(res["bias"] - 1.0) < 1e-9

    def test_worst_sorted_by_abs_error(self):
        a = ErrorAnalyzer(top_k=2)
        res = a.analyze_regression([10.0, 20.0, 30.0], [11.0, 25.0, 30.5])
        assert res["worst_cases"][0]["index"] == 1  # خطأ 5
        assert res["worst_cases"][0]["abs_error"] == 5.0

    def test_clinically_dangerous(self):
        a = ErrorAnalyzer(tolerance=1.0)
        res = a.analyze_regression([10.0], [15.0])
        assert res["n_clinically_dangerous"] == 1
        assert res["pct_clinically_dangerous"] == 100.0

    def test_by_target_range_bins(self):
        a = ErrorAnalyzer(n_bins=3)
        res = a.analyze_regression(list(range(10)), list(range(10)))
        assert set(res["by_target_range"].keys()) == {"bin_0", "bin_1", "bin_2"}
        assert all(res["by_target_range"][b]["count"] > 0 for b in res["by_target_range"])

    def test_empty_regression(self):
        res = ErrorAnalyzer().analyze_regression([], [])
        assert res["n"] == 0
        assert res["worst_cases"] == []

    def test_ci_width_in_worst(self):
        a = ErrorAnalyzer()
        per = [{"ci_width": 2.0}, {"ci_width": 8.0}]
        res = a.analyze_regression([10.0, 20.0], [11.0, 30.0], per_sample=per)
        widths = {w["index"]: w.get("ci_width") for w in res["worst_cases"]}
        assert widths[1] == 8.0


class TestCorrelate:
    def test_perfect_calibration(self):
        a = ErrorAnalyzer()
        res = a.correlate_with_uncertainty([1.0, 2.0, 3.0, 4.0, 5.0],
                                           [1.0, 2.0, 3.0, 4.0, 5.0])
        assert abs(res["pearson"] - 1.0) < 1e-9
        assert res["well_calibrated"] is True
        assert res["mean_error_high_unc"] > res["mean_error_low_unc"]

    def test_no_correlation(self):
        a = ErrorAnalyzer()
        res = a.correlate_with_uncertainty([5.0, 5.0, 5.0, 5.0],
                                           [1.0, 2.0, 3.0, 4.0])
        assert res["pearson"] == 0.0
        assert res["well_calibrated"] is False

    def test_length_mismatch_raises(self):
        with pytest.raises(ValueError):
            ErrorAnalyzer().correlate_with_uncertainty([1.0], [1.0, 2.0])

    def test_single_returns_safe(self):
        res = ErrorAnalyzer().correlate_with_uncertainty([1.0], [1.0])
        assert res["n"] == 1
        assert res["well_calibrated"] is False


class TestGuards:
    def test_invalid_tolerance(self):
        with pytest.raises(ValueError):
            ErrorAnalyzer(tolerance=0)

    def test_invalid_bins(self):
        with pytest.raises(ValueError):
            ErrorAnalyzer(n_bins=0)

    def test_invalid_top_k(self):
        with pytest.raises(ValueError):
            ErrorAnalyzer(top_k=0)
