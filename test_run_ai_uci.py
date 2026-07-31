"""
ProtonAI - Test Stage-4 AI Runner
اختبارات مايسترو المرحلة 4
"""

import csv
import io
import random
import pytest
from run_ai_uci import run_ai_analysis
from dose_engine import STATUS_NA, STATUS_IN_RANGE
from model_registry import ModelRegistry
from experiment_tracker import ExperimentTracker

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


def _reg_records(n=60):
    random.seed(9)
    out = []
    for i in range(n):
        age = 30 + (i % 40)
        vol = 50 + (i % 150)
        dose = 60 + 0.1 * age + 0.01 * vol + random.uniform(-1, 1)
        out.append({"age": age, "volume": vol, "tumor_type": "lung",
                    "dose": round(dose, 2)})
    return out


WIDE = {"lung": (0.0, 10000.0)}


class TestClassification:
    def test_task(self):
        res = run_ai_analysis(_load_uci())
        assert res["task"] == "classification"

    def test_comparison_three_models(self):
        res = run_ai_analysis(_load_uci())
        assert len(res["comparison"]["table"]) == 3
        assert set(res["comparison"]["ranking"]) == {"single", "tuned", "ensemble"}

    def test_dose_not_applicable(self):
        res = run_ai_analysis(_load_uci())
        assert res["dose"]["protocol"]["status"] == STATUS_NA
        assert res["dose"]["unit"] is None

    def test_explanation_predicted_label(self):
        res = run_ai_analysis(_load_uci())
        assert res["explanation"]["local"]["predicted"] in ("M", "B")

    def test_top_features_count(self):
        res = run_ai_analysis(_load_uci(), top_k=3)
        assert len(res["explanation"]["top_features"]) == 3

    def test_verified_and_valid(self):
        res = run_ai_analysis(_load_uci())
        assert res["reproducibility"]["verified"] is True
        assert res["verification"]["valid"] is True

    def test_lineage_has_experiment(self):
        res = run_ai_analysis(_load_uci())
        assert "experiment" in res["lineage"]

    def test_report_sections(self):
        md = run_ai_analysis(_load_uci())["report_markdown"]
        for sec in ["Model Comparison", "Reproducibility", "Explanation",
                    "Dose Engine", "Registry"]:
            assert sec in md

    def test_train_test_sum(self):
        res = run_ai_analysis(_load_uci())
        assert res["train"] + res["test"] == 20


class TestRegression:
    def test_dose_in_range(self):
        res = run_ai_analysis(_reg_records(), feature_columns=["age", "volume"],
                              target_column="dose", protocols=WIDE)
        assert res["task"] == "regression"
        assert res["dose"]["protocol"]["status"] == STATUS_IN_RANGE

    def test_unit_gy_rbe(self):
        res = run_ai_analysis(_reg_records(), feature_columns=["age", "volume"],
                              target_column="dose", protocols=WIDE)
        assert res["dose"]["unit"] == "Gy(RBE)"

    def test_uncertainty_present(self):
        res = run_ai_analysis(_reg_records(), feature_columns=["age", "volume"],
                              target_column="dose", protocols=WIDE)
        u = res["dose"]["uncertainty"]
        assert u is not None
        assert u["ci_low"] <= res["dose"]["predicted"] <= u["ci_high"]


class TestRegistryInjection:
    def test_registry_populated(self, tmp_path):
        reg = ModelRegistry(tmp_path / "r")
        res = run_ai_analysis(_load_uci(), registry=reg)
        assert len(reg.list_all()) == 1
        assert reg.list_all()[0].model_id == res["reproducibility"]["model_id"]

    def test_model_loadable(self, tmp_path):
        reg = ModelRegistry(tmp_path / "r")
        res = run_ai_analysis(_load_uci(), registry=reg)
        loaded = reg.load_model(res["reproducibility"]["model_id"])
        assert loaded.is_trained is True

    def test_version_is_one(self, tmp_path):
        reg = ModelRegistry(tmp_path / "r")
        run_ai_analysis(_load_uci(), registry=reg)
        assert reg.list_all()[0].version == 1


class TestTrackerInjection:
    def test_tracker_records_one(self):
        trk = ExperimentTracker()
        res = run_ai_analysis(_load_uci(), tracker=trk)
        assert len(trk.experiments) == 1
        assert trk.experiments[0].experiment_id == res["reproducibility"]["experiment_id"]


class TestSave:
    def test_saves_all_files(self, tmp_path):
        out = tmp_path / "o"
        run_ai_analysis(_load_uci(), output_dir=out)
        assert (out / "ai_report.md").exists()
        assert (out / "ai_report.json").exists()
        assert (out / "registry.json").exists()
        assert (out / "experiments.json").exists()
        assert (out / "ensemble_product.pkl").exists()


class TestDeterministic:
    def test_fingerprints_stable(self):
        r1 = run_ai_analysis(_load_uci())
        r2 = run_ai_analysis(_load_uci())
        assert r1["reproducibility"]["data_fingerprint"] == r2["reproducibility"]["data_fingerprint"]
        assert r1["reproducibility"]["split_fingerprint"] == r2["reproducibility"]["split_fingerprint"]


class TestGuards:
    def test_empty_records_raises(self):
        with pytest.raises(ValueError):
            run_ai_analysis([])
