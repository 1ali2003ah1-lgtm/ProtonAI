"""
ProtonAI - Test Clinical Loader
اختبارات مستقبل بيانات المستشفى
"""

import pytest
from clinical_loader import ClinicalDataLoader, _normalize


def _write_csv(path, text):
    path.write_text(text.strip() + "\n", encoding="utf-8")


class TestNormalize:
    def test_normalize_removes_spaces_and_symbols(self):
        assert _normalize("Patient ID") == "patientid"
        assert _normalize("Age (Years)") == "ageyears"
        assert _normalize("  SEX ") == "sex"


class TestClinicalLoader:

    def test_load_csv_with_fuzzy_headers(self, tmp_path):
        """أسماء أعمدة غريبة تُطابق بذكاء"""
        f = tmp_path / "hospital.csv"
        _write_csv(f, """Patient ID,Age (Years),Sex,Tumor
H001,55,M,lung
H002,62,F,breast""")

        rows = ClinicalDataLoader().load(f)
        assert len(rows) == 2
        assert rows[0]["patient_id"] == "H001"
        assert rows[0]["age"] == 55
        assert rows[0]["gender"] == "M"
        assert rows[0]["tumor_type"] == "lung"

    def test_load_json_with_manual_mapping(self, tmp_path):
        """mapping يدوي لأسماء غير معتادة"""
        f = tmp_path / "data.json"
        f.write_text(
            '[{"pid":"X1","yrs":70,"g":"F","dx":"brain"}]',
            encoding="utf-8",
        )
        loader = ClinicalDataLoader(mapping={
            "patient_id": ["pid"],
            "age": ["yrs"],
            "gender": ["g"],
            "tumor_type": ["dx"],
        })
        rows = loader.load(f)
        assert rows[0]["patient_id"] == "X1"
        assert rows[0]["age"] == 70
        assert rows[0]["tumor_type"] == "brain"

    def test_validate_separates_invalid_with_reason(self, tmp_path):
        """سجل بعمر سالب يُرفض مع سبب"""
        f = tmp_path / "mix.csv"
        _write_csv(f, """patient_id,age,gender,tumor_type
P1,45,M,lung
P2,-5,F,brain""")

        report = ClinicalDataLoader().load_and_validate(f)
        assert report["valid_count"] == 1
        assert report["invalid_count"] == 1
        assert report["invalid"][0]["reason"]  # فيه سبب مسجّل

    def test_prostate_young_rejected(self, tmp_path):
        """prostate بعمر 30 يُرفض (قاعدة سريرية)"""
        f = tmp_path / "p.csv"
        _write_csv(f, """patient_id,age,gender,tumor_type
P1,30,M,prostate""")

        report = ClinicalDataLoader().load_and_validate(f)
        assert report["invalid_count"] == 1
        assert "العمر" in report["invalid"][0]["reason"]

    def test_missing_gender_rejected(self, tmp_path):
        """غياب عمود الجنس يرفض السجلات"""
        f = tmp_path / "nog.csv"
        _write_csv(f, """patient_id,age,tumor_type
P1,45,lung""")

        report = ClinicalDataLoader().load_and_validate(f)
        assert report["valid_count"] == 0
        assert report["invalid_count"] == 1

    def test_empty_csv_returns_empty(self, tmp_path):
        """ملف فيه عناوين فقط بدون بيانات"""
        f = tmp_path / "empty.csv"
        _write_csv(f, """patient_id,age,gender,tumor_type""")

        report = ClinicalDataLoader().load_and_validate(f)
        assert report["total"] == 0
        assert report["acceptance_rate"] == "0.0%"

    def test_load_missing_file_raises(self, tmp_path):
        loader = ClinicalDataLoader()
        with pytest.raises(FileNotFoundError):
            loader.load(tmp_path / "nope.csv")

    def test_unsupported_format_raises(self, tmp_path):
        f = tmp_path / "x.txt"
        f.write_text("hello", encoding="utf-8")
        with pytest.raises(ValueError):
            ClinicalDataLoader().load(f)
