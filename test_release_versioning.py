"""
ProtonAI - Test Release Versioning
اختبارات الترقيم الدلالي + الإصدار + checklist
"""

import pytest
from release_versioning import (
    SemanticVersion, ReleaseManager, DEFAULT_CHECKLIST,
)


class TestSemanticVersion:
    def test_parse_str(self):
        v = SemanticVersion.parse("1.2.3")
        assert str(v) == "1.2.3"

    def test_parse_invalid(self):
        with pytest.raises(ValueError):
            SemanticVersion.parse("1.2")
        with pytest.raises(ValueError):
            SemanticVersion.parse("a.b.c")

    def test_negative_raises(self):
        with pytest.raises(ValueError):
            SemanticVersion(-1, 0, 0)

    def test_bumps(self):
        v = SemanticVersion(1, 2, 3)
        assert str(v.bump_major()) == "2.0.0"
        assert str(v.bump_minor()) == "1.3.0"
        assert str(v.bump_patch()) == "1.2.4"

    def test_compare(self):
        assert SemanticVersion(1, 0, 0) < SemanticVersion(1, 1, 0)
        assert SemanticVersion(1, 0, 0) == SemanticVersion(1, 0, 0)


class TestAddChange:
    def test_invalid_kind_raises(self):
        rm = ReleaseManager()
        with pytest.raises(ValueError):
            rm.add_change("x", "weird")

    def test_pending_recorded(self):
        rm = ReleaseManager()
        rm.add_change("ميزة جديدة", "feature")
        assert len(rm.pending) == 1


class TestChangelog:
    def test_groups_by_kind(self):
        rm = ReleaseManager()
        rm.add_change("كسر", "breaking")
        rm.add_change("ميزة", "feature")
        md = rm.changelog()
        assert "تغييرات كاسرة" in md
        assert "ميزات" in md
        assert "- كسر" in md

    def test_empty_note(self):
        assert "لا تغييرات" in ReleaseManager().changelog()


class TestRelease:
    def test_feature_bumps_minor(self):
        rm = ReleaseManager("1.2.3")
        rm.add_change("ميزة", "feature")
        rec = rm.release()
        assert rec["version"] == "1.3.0"
        assert rec["bump"] == "feature"

    def test_breaking_bumps_major(self):
        rm = ReleaseManager("1.2.3")
        rm.add_change("كسر", "breaking")
        rm.add_change("ميزة", "feature")
        assert rm.release()["version"] == "2.0.0"

    def test_fix_bumps_patch(self):
        rm = ReleaseManager("1.2.3")
        rm.add_change("إصلاح", "fix")
        assert rm.release()["version"] == "1.2.4"

    def test_no_changes_raises(self):
        with pytest.raises(ValueError):
            ReleaseManager().release()

    def test_release_resets_pending_and_records(self):
        rm = ReleaseManager()
        rm.add_change("ميزة", "feature")
        rm.release()
        assert rm.pending == []
        assert len(rm.releases) == 1

    def test_record_has_checklist_and_ready(self):
        rm = ReleaseManager()
        rm.add_change("ميزة", "feature")
        rec = rm.release()
        assert rec["ready_to_launch"] is False  # checklist فاضي
        assert set(rec["checklist"].keys()) == set(DEFAULT_CHECKLIST)


class TestChecklist:
    def test_initially_not_ready(self):
        assert ReleaseManager().ready_to_launch() is False

    def test_all_green_ready(self):
        rm = ReleaseManager()
        for item in DEFAULT_CHECKLIST:
            rm.set_check(item, True)
        assert rm.ready_to_launch() is True

    def test_one_red_not_ready(self):
        rm = ReleaseManager()
        for item in DEFAULT_CHECKLIST:
            rm.set_check(item, True)
        rm.set_check("tests_green", False)
        assert rm.ready_to_launch() is False

    def test_unknown_item_raises(self):
        with pytest.raises(ValueError):
            ReleaseManager().set_check("nope", True)
