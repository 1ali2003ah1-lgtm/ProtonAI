"""
ProtonAI - Test Scientific UCI Analysis
اختبارات التحليل العلمي الكامل
"""

import csv
import io
import pytest
from run_scientific_uci import run_scientific_analysis

UCI_CSV = """id,diagnosis,radius_mean,texture_mean,perimeter_mean,area_mean,smoothness_mean
842302,M,17.99,10.38,122.8,1001,0.1184
842517,M,20.57,17.77,132.9,1326,0.08474
84300903,M,19.69,21.25,130,1203,0.1096
84348301,M,11.42,20.38,77.58,386.1,0.1425
84358402,M,20.29,14.34,135.1,1297,0.1003
843786,M,12.45,15.7,82.57,477.1,0.1278
844359,M,18.25,19.98,119.6,1001,0.09463
84458202,M,13.71,20.83,90.2,577.9,0.1189
844981,M,13,21.82,87.5,519.8,0.1273
84501001,M,12.46,24.04,83.97,475.9,0.1186
8510426,B,13.54,14.36,87.46,566.3,0.09779
8510653,B,13.08,15.71,85.63,520,0.1075
8510824,B,9.504,12.44,60.34,273.9,0.1024
85713702,B,14.78,23.94,97.4,668.3,0.1172
857155,B,13.77,22.29,90.63,588.9,0.12
857156,B,13.96,17.05,91.43,602.4,0.1096
857343,B,14.78,17.67,94.68,673.6,0.09179
857373,B,13.64,16.34,87.21,571.8,0.07685
857374,B,12.42,15.04,78.61,476.5,0.07926
858477,B,13.27,14.76,84.74,551.7,0.07355
"""


def _load_uci():
    return list(csv.DictReader(io.StringIO(UCI_CSV.strip())))


def _reg_records(n=40):
    import random
    random.seed(3)
    return [{"x": float(i), "z": float(i) * 2, "y": 3 * i + random.uniform(-5, 5)}
            for i in range(n)]


class TestClassificationPath:
    def test_task_is_classification(self):
        res = run_scientific_analysis(_load_uci(), k=2)
        assert res["task"] == "classification"

    def test_evaluation_has_accuracy(self):
        res = run_scientific_analysis(_load_uci(), k=2)
        assert 0.0 <= res["evaluation"]["accuracy"] <= 1.0

    def test_uncertainty_samples_match_test(self):
        res = run_scientific_analysis(_load_uci(), k=2)
        assert res["uncertainty"]["samples"] == res["test"]

    def test_error_n_matches_test(self):
        res = run_scientific_analysis(_load_uci(), k=2)
        assert res["error"]["n"] == res["test"]

    def test_benchmark_verdict_is_bool(self):
        res = run_scientific_analysis(_load_uci(), k=2)
        assert res["benchmark"]["verdict"]["beats_all_baselines"] in (True, False)
        assert "majority_class" in res["benchmark"]["baselines"]

    def test_physician_review_stats(self):
        res = run_scientific_analysis(_load_uci(), k=2)
        assert res["physician_review"]["total_flagged"] >= 0

    def test_train_test_sizes(self):
        res = run_scientific_analysis(_load_uci(), k=2)
        assert res["train"] + res["test"] == 20


class TestReproducibility:
    def test_fingerprints_present(self):
        res = run_scientific_analysis(_load_uci(), k=2)
        assert len(res["reproducibility"]["data_fingerprint"]) == 64
        assert len(res["reproducibility"]["split_fingerprint"]) == 64
        assert res["reproducibility"]["experiment_id"]

    def test_deterministic_across_runs(self):
        r1 = run_scientific_analysis(_load_uci(), k=2, seed=42)
        r2 = run_scientific_analysis(_load_uci(), k=2, seed=42)
        assert r1["reproducibility"]["data_fingerprint"] == r2["reproducibility"]["data_fingerprint"]
        assert r1["reproducibility"]["split_fingerprint"] == r2["reproducibility"]["split_fingerprint"]

    def test_different_seed_different_split(self):
        r1 = run_scientific_analysis(_load_uci(), k=2, seed=1)
        r2 = run_scientific_analysis(_load_uci(), k=2, seed=2)
        assert r1["reproducibility"]["split_fingerprint"] != r2["reproducibility"]["split_fingerprint"]


class TestCrossValidation:
    def test_cv_included_when_enabled(self):
        res = run_scientific_analysis(_load_uci(), k=2, run_cv=True)
        assert res["cross_validation"] is not None
        assert res["cross_validation"]["k"] == 2

    def test_cv_skipped_when_disabled(self):
        res = run_scientific_analysis(_load_uci(), k=2, run_cv=False)
        assert res["cross_validation"] is None


class TestRegressionPath:
    def test_regression_task(self):
        res = run_scientific_analysis(
            _reg_records(), feature_columns=["x", "z"], target_column="y",
            k=2, run_cv=False)
        assert res["task"] == "regression"
        assert "mae" in res["evaluation"]

    def test_calibration_present_for_regression(self):
        res = run_scientific_analysis(
            _reg_records(), feature_columns=["x", "z"], target_column="y",
            k=2, run_cv=False)
        assert res["calibration"] is not None
        assert "pearson" in res["calibration"]


class TestReportAndSave:
    def test_markdown_contains_sections(self):
        res = run_scientific_analysis(_load_uci(), k=2)
        md = res["report_markdown"]
        assert "# ProtonAI Scientific Analysis" in md
        assert "Benchmark" in md
        assert "Physician Review" in md
        assert "Reproducibility" in md

    def test_saves_files(self, tmp_path):
        out = tmp_path / "sci"
        run_scientific_analysis(_load_uci(), output_dir=out, k=2)
        assert (out / "scientific_report.md").exists()
        assert (out / "scientific_report.json").exists()
        assert (out / "experiments.json").exists()
        assert (out / "physician_review.json").exists()


class TestGuards:
    def test_too_few_records_raises(self):
        with pytest.raises(ValueError):
            run_scientific_analysis(_load_uci()[:3])
