"""
ProtonAI - Test Clinical Runner
اختبارات سكربت تشغيل البيانات السريرية
"""

import json
from run_clinical import run_clinical_report


def _write_csv(path, text):
    path.write_text(text.strip() + "\n", encoding="utf-8")


def test_run_clinical_report_counts(tmp_path):
    f = tmp_path / "h.csv"
    _write_csv(f, """patient_id,age,gender,tumor_type
P1,50,M,lung
P2,-3,F,brain""")

    report = run_clinical_report(f)
    assert report["total"] == 2
    assert report["valid_count"] == 1
    assert report["invalid_count"] == 1
    assert "source_file" in report


def test_run_clinical_report_saves_json(tmp_path):
    f = tmp_path / "h.csv"
    _write_csv(f, """patient_id,age,gender,tumor_type
P1,50,M,lung""")

    out = tmp_path / "out" / "report.json"
    report = run_clinical_report(f, output_path=out)

    assert out.exists()
    with open(out, "r", encoding="utf-8") as fh:
        saved = json.load(fh)
    assert saved["valid_count"] == report["valid_count"]
