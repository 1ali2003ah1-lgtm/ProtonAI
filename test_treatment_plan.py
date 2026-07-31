"""
ProtonAI - Test Treatment Plan
اختبارات كائن الخطة العلاجية الموحّد
"""

import pytest
from treatment_plan import TreatmentPlan, SECTIONS, new_plan_id


class TestInit:
    def test_basic(self):
        p = TreatmentPlan("p1", "anon_123")
        assert p.plan_id == "p1"
        assert p.patient_id == "anon_123"
        assert p.imaging == {}
        assert p.notes == ""

    def test_empty_plan_id_raises(self):
        with pytest.raises(ValueError):
            TreatmentPlan("", "anon")

    def test_empty_patient_id_raises(self):
        with pytest.raises(ValueError):
            TreatmentPlan("p1", "")

    def test_whitespace_patient_id_raises(self):
        with pytest.raises(ValueError):
            TreatmentPlan("p1", "   ")

    def test_created_at_auto_filled(self):
        p = TreatmentPlan("p1", "a")
        assert p.created_at  # غير فارغ


class TestSetSection:
    def test_set_imaging(self):
        p = TreatmentPlan("p1", "a")
        p.set_section("imaging", {"slices": 100})
        assert p.imaging == {"slices": 100}

    def test_set_each_section(self):
        p = TreatmentPlan("p1", "a")
        for s in SECTIONS:
            p.set_section(s, {"v": 1})
            assert p.section_filled(s) is True

    def test_unknown_section_raises(self):
        p = TreatmentPlan("p1", "a")
        with pytest.raises(ValueError):
            p.set_section("weird", {})

    def test_non_dict_raises(self):
        p = TreatmentPlan("p1", "a")
        with pytest.raises(TypeError):
            p.set_section("imaging", "not a dict")

    def test_set_section_copies_not_references(self):
        p = TreatmentPlan("p1", "a")
        d = {"x": 1}
        p.set_section("physics", d)
        d["x"] = 999  # تعديل الأصل
        assert p.physics["x"] == 1  # الخطة تحتفظ بالنسخة


class TestCompleteness:
    def test_empty_is_zero(self):
        p = TreatmentPlan("p1", "a")
        assert p.completeness() == 0.0
        assert p.is_complete() is False
        assert p.missing_sections() == list(SECTIONS)

    def test_half_filled(self):
        p = TreatmentPlan("p1", "a")
        p.set_section("imaging", {"x": 1})
        p.set_section("physics", {"y": 2})
        assert p.completeness() == 0.5
        assert p.is_complete() is False
        assert set(p.missing_sections()) == {"ai", "reviews"}

    def test_full_is_complete(self):
        p = TreatmentPlan("p1", "a")
        for s in SECTIONS:
            p.set_section(s, {"v": 1})
        assert p.completeness() == 1.0
        assert p.is_complete() is True
        assert p.missing_sections() == []

    def test_section_filled_unknown_raises(self):
        p = TreatmentPlan("p1", "a")
        with pytest.raises(ValueError):
            p.section_filled("weird")


class TestPersistence:
    def test_roundtrip_preserves_data(self):
        p = TreatmentPlan("p1", "a", notes="hi")
        p.set_section("ai", {"pred": "M"})
        p2 = TreatmentPlan.from_dict(p.to_dict())
        assert p2.plan_id == "p1"
        assert p2.patient_id == "a"
        assert p2.notes == "hi"
        assert p2.ai == {"pred": "M"}

    def test_from_dict_defaults_missing_sections(self):
        p = TreatmentPlan.from_dict({"plan_id": "x", "patient_id": "y"})
        assert p.imaging == {}
        assert p.physics == {}
        assert p.created_at  # افتراضي

    def test_from_dict_copies_sections(self):
        src = {"plan_id": "x", "patient_id": "y", "ai": {"k": 1}}
        p = TreatmentPlan.from_dict(src)
        src["ai"]["k"] = 999
        assert p.ai["k"] == 1  # نسخة، لا مرجع

    def test_from_dict_validates(self):
        with pytest.raises(ValueError):
            TreatmentPlan.from_dict({"plan_id": "", "patient_id": "y"})


class TestSummary:
    def test_keys_present(self):
        p = TreatmentPlan("p1", "a")
        s = p.summary()
        for k in ["plan_id", "patient_id", "completeness",
                  "is_complete", "missing_sections", "created_at"]:
            assert k in s

    def test_summary_reflects_state(self):
        p = TreatmentPlan("p1", "a")
        p.set_section("imaging", {"x": 1})
        s = p.summary()
        assert s["completeness"] == 0.25
        assert s["is_complete"] is False


class TestNewPlanId:
    def test_length(self):
        assert len(new_plan_id()) == 12

    def test_unique(self):
        ids = {new_plan_id() for _ in range(50)}
        assert len(ids) == 50  # كلهم فريدون
