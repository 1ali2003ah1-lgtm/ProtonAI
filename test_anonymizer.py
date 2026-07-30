"""
ProtonAI - Test Anonymizer
اختبارات وحدة إخفاء الهوية
"""

import pytest
from anonymizer import Anonymizer, DEFAULT_SENSITIVE_FIELDS


def _rec():
    return {
        "patient_id": "REAL-123",
        "age": 95,
        "gender": "M",
        "tumor_type": "lung",
        "name": "Ahmed Ali",
        "dob": "1930-01-01",
        "phone": "0770000000",
    }


class TestHashId:
    def test_deterministic(self):
        a = Anonymizer(salt="s1")
        assert a.hash_id("P1") == a.hash_id("P1")

    def test_prefix(self):
        assert Anonymizer().hash_id("P1").startswith("ANON_")

    def test_different_salt_different_hash(self):
        h1 = Anonymizer(salt="a").hash_id("P1")
        h2 = Anonymizer(salt="b").hash_id("P1")
        assert h1 != h2

    def test_hides_original(self):
        assert "REAL-123" not in Anonymizer().hash_id("REAL-123")


class TestGeneralizeAge:
    def test_bucket_over_89(self):
        assert Anonymizer().generalize_age(95) == "90+"

    def test_bucket_range(self):
        assert Anonymizer().generalize_age(55) == "50-59"
        assert Anonymizer().generalize_age(0) == "0-9"

    def test_cap_over_89(self):
        assert Anonymizer(age_strategy="cap").generalize_age(95) == 90

    def test_cap_under_89_unchanged(self):
        assert Anonymizer(age_strategy="cap").generalize_age(50) == 50

    def test_invalid_strategy_raises(self):
        with pytest.raises(ValueError):
            Anonymizer(age_strategy="weird")


class TestAnonymizeRecord:
    def test_patient_id_replaced(self):
        anon, log = Anonymizer(salt="x").anonymize_record(_rec())
        assert anon["patient_id"].startswith("ANON_")
        assert anon["patient_id"] != "REAL-123"
        assert log.ids_hashed == 1

    def test_sensitive_fields_removed(self):
        anon, log = Anonymizer().anonymize_record(_rec())
        for f in ["name", "dob", "phone"]:
            assert f not in anon
        assert log.fields_removed["name"] == 1

    def test_non_sensitive_kept(self):
        anon, _ = Anonymizer().anonymize_record(_rec())
        assert anon["gender"] == "M"
        assert anon["tumor_type"] == "lung"

    def test_age_generalized(self):
        anon, log = Anonymizer().anonymize_record(_rec())
        assert anon["age"] == "90+"
        assert log.ages_generalized == 1

    def test_original_not_mutated(self):
        original = _rec()
        before = dict(original)
        Anonymizer().anonymize_record(original)
        assert original == before  # الأصل سالم تماماً

    def test_missing_fields_no_crash(self):
        anon, log = Anonymizer().anonymize_record({"tumor_type": "brain"})
        assert log.ids_hashed == 0
        assert log.ages_generalized == 0
        assert anon["tumor_type"] == "brain"


class TestAnonymizeBatch:
    def test_same_length(self):
        recs = [_rec(), _rec()]
        out, report = Anonymizer(salt="x").anonymize_batch(recs)
        assert len(out) == 2
        assert report.records == 2

    def test_report_counts(self):
        recs = [_rec(), _rec()]
        _, report = Anonymizer(salt="x").anonymize_batch(recs)
        assert report.ids_hashed == 2
        assert report.ages_generalized == 2
        assert report.fields_removed["name"] == 2

    def test_summary_keys(self):
        _, report = Anonymizer().anonymize_batch([_rec()])
        assert set(report.summary().keys()) == {
            "records", "ids_hashed", "ages_generalized", "fields_removed"
        }

    def test_consistent_ids_across_batch(self):
        a = Anonymizer(salt="x")
        out1, _ = a.anonymize_batch([{"patient_id": "P1"}])
        out2, _ = a.anonymize_batch([{"patient_id": "P1"}])
        assert out1[0]["patient_id"] == out2[0]["patient_id"]

    def test_custom_sensitive_fields(self):
        a = Anonymizer(sensitive_fields=["tumor_type"])
        anon, _ = a.anonymize_record(_rec())
        assert "tumor_type" not in anon
        assert "name" in anon  # ما انحذف لأنه مو بالقائمة المخصصة
