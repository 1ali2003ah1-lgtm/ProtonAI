"""
ProtonAI - Test Scientific Report
اختبارات مولّد التقارير العلمية
"""

import json
import pytest
from scientific_report import ScientificReport, format_ci, _fmt
from scientific_evaluator import ScientificEvaluator
from generic_model import GenericModel


def _class_data(n=60):
    data = []
    for i in range(n):
        v = 10 + i
        data.append({"f1": v, "f2": v * 2, "label": "M" if v > 40 else "B"})
    return data


class TestFormatters:
    def test_fmt_float(self):
        assert _fmt(0.123456) == "0.1235"

    def test_fmt_non_float(self):
        assert _fmt("hello") == "hello"

    def test_format_ci_contains_brackets_and_dash(self):
        s = format_ci(0.9, 0.85, 0.95)
        assert "[" in s and "–" in s and "]" in s
        assert "0.9000" in s


class TestReportBasics:
    def test_init_defaults(self):
        r = ScientificReport()
        assert r.title
        assert r.sections == []

    def test_add_section(self):
        r = ScientificReport()
        r.add_section("Test", {"type": "metrics", "data": {"accuracy": 0.9}})
        assert len(r.sections) == 1

    def test_to_dict_keys(self):
        r = ScientificReport(title="T", author="A", dataset_name="D")
        d = r.to_dict()
        assert d["title"] == "T"
        assert d["author"] == "A"
        assert d["dataset_name"] == "D"
        assert "metadata" in d
        assert "sections" in d


class TestRenderMetrics:
    def test_metrics_section_in_markdown(self):
        r = ScientificReport()
        r.add_metrics({"task": "classification", "accuracy": 0.95, "f1_macro": 0.93, "samples": 60})
        md = r.to_markdown()
        assert "accuracy" in md
        assert "0.9500" in md

    def test_metrics_table_with_ci(self):
        r = ScientificReport()
        r.add_cross_validation({
            "task": "classification", "k": 3, "n": 60, "stratified": True,
            "mean_metrics": {"accuracy": 0.9},
            "ci_metrics": {"accuracy": {"ci_low": 0.85, "ci_high": 0.95}},
        })
        md = r.to_markdown()
        assert "0.9000" in md
        assert "0.8500" in md


class TestRenderComparison:
    def test_comparison_ranking_order(self):
        r = ScientificReport()
        r.add_comparison({
            "primary_metric": "accuracy",
            "higher_better": True,
            "ranking": ["big", "small"],
            "results": {
                "big": {"mean_metrics": {"accuracy": 0.95},
                        "ci_metrics": {"accuracy": {"ci_low": 0.9, "ci_high": 0.98}}},
                "small": {"mean_metrics": {"accuracy": 0.8},
                          "ci_metrics": {"accuracy": {"ci_low": 0.7, "ci_high": 0.88}}},
            },
        })
        md = r.to_markdown()
        assert "big" in md and "small" in md
        assert md.index("big") < md.index("small")

    def test_comparison_shows_primary_metric(self):
        r = ScientificReport()
        r.add_comparison({
            "primary_metric": "mae", "higher_better": False,
            "ranking": ["m1"], "results": {"m1": {"mean_metrics": {"mae": 1.2}, "ci_metrics": {}}},
        })
        md = r.to_markdown()
        assert "mae" in md
        assert "lower is better" in md


class TestRenderCV:
    def test_cv_section_fields(self):
        r = ScientificReport()
        r.add_cross_validation({
            "task": "regression", "k": 5, "n": 100, "stratified": False,
            "mean_metrics": {"mae": 1.2},
            "ci_metrics": {"mae": {"ci_low": 1.0, "ci_high": 1.4}},
        })
        md = r.to_markdown()
        assert "mae" in md
        assert "Folds" in md


class TestSave:
    def test_save_markdown(self, tmp_path):
        r = ScientificReport(title="X")
        r.add_metrics({"task": "classification", "accuracy": 0.9, "samples": 10})
        p = tmp_path / "out" / "report.md"
        r.save_markdown(p)
        assert p.exists()
        assert "# X" in p.read_text(encoding="utf-8")

    def test_save_json(self, tmp_path):
        r = ScientificReport(title="X")
        r.add_metrics({"task": "classification", "accuracy": 0.9, "samples": 10})
        p = tmp_path / "report.json"
        r.save_json(p)
        assert p.exists()
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        assert d["title"] == "X"


class TestEndToEnd:
    def test_full_report_from_real_cv(self):
        ev = ScientificEvaluator()
        cv = ev.cross_validate(_class_data(), lambda: GenericModel(["f1", "f2"], "label"), k=3)
        r = ScientificReport(title="UCI Report", dataset_name="UCI")
        r.add_cross_validation(cv)
        md = r.to_markdown()
        assert "accuracy" in md
        assert "UCI" in md
