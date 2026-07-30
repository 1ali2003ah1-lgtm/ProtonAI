"""
ProtonAI - Test UCI Training Runner
اختبارات أول تدريب حقيقي على بيانات UCI المعتمدة
"""

import json
import pytest
from run_uci_training import run_uci, UCI_FEATURES, UCI_TARGET

# عينة حقيقية من UCI Breast Cancer Wisconsin (10 خبيث M + 10 حميد B)
UCI_SAMPLE = """id,diagnosis,radius_mean,texture_mean,perimeter_mean,area_mean,smoothness_mean
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


@pytest.fixture
def uci_csv(tmp_path):
    f = tmp_path / "uci_sample.csv"
    f.write_text(UCI_SAMPLE.strip() + "\n", encoding="utf-8")
    return f


class TestUCITraining:
    def test_run_uci_success(self, uci_csv, tmp_path):
        report = run_uci(uci_csv, output_dir=tmp_path / "out", train_ratio=1.0)
        assert report.status == "success"
        assert report.succeeded is True

    def test_contract_accepts_uci(self, uci_csv, tmp_path):
        report = run_uci(uci_csv, output_dir=tmp_path / "out", train_ratio=1.0)
        assert report.contract is not None
        assert report.contract["is_acceptable"] is True

    def test_classification_accuracy(self, uci_csv, tmp_path):
        report = run_uci(uci_csv, output_dir=tmp_path / "out", train_ratio=1.0)
        assert report.evaluation["task"] == "classification"
        assert report.evaluation["accuracy"] >= 0.85

    def test_loaded_count(self, uci_csv, tmp_path):
        report = run_uci(uci_csv, output_dir=tmp_path / "out", train_ratio=1.0)
        assert report.loaded == 20

    def test_report_saved(self, uci_csv, tmp_path):
        out = tmp_path / "out"
        run_uci(uci_csv, output_dir=out, train_ratio=1.0)
        assert (out / "uci_report.json").exists()
        with open(out / "uci_report.json", encoding="utf-8") as f:
            data = json.load(f)
        assert data["status"] == "success"

    def test_model_saved(self, uci_csv, tmp_path):
        out = tmp_path / "out"
        run_uci(uci_csv, output_dir=out, train_ratio=1.0)
        assert (out / "uci_model.pkl").exists()

    def test_features_and_target(self):
        assert UCI_TARGET == "diagnosis"
        assert "radius_mean" in UCI_FEATURES
        assert len(UCI_FEATURES) == 5
