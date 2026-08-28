"""
ProtonAI - Test Board × Intelligence
"""

from board_intelligence import board_section, combine
from clinical_intelligence import ClinicalIntelligence
from tumor_board import Opinion, TumorBoard


def make_report(status="GREEN"):
    return ClinicalIntelligence().synthesize(
        "P-200", "prostate", status=status,
        achieved_oars={"rectum_V70": 10})


def make_board(decision="PROCEED"):
    b = TumorBoard("P-200")
    b.add(Opinion("د. أ", "oncologist", decision, 0.9))
    b.add(Opinion("د. ب", "physicist", decision, 0.8))
    return b.decide()


class TestSection:
    def test_contains_decision(self):
        s = board_section(make_board())
        assert "PROCEED" in s and "الإجماع" in s


class TestCombine:
    def test_board_fields(self):
        r = combine(make_report(), make_board())
        assert r["synthesis"]["board_decision"] == "PROCEED"
        assert "قرار مجلس الورم" in r["narrative"]

    def test_stop_overrides(self):
        b = TumorBoard("P-200")
        b.add(Opinion("د. أ", "oncologist", "PROCEED", 0.9))
        b.add(Opinion("د. ب", "physicist", "STOP", 0.9))
        r = combine(make_report(), b.decide())
        assert r["synthesis"]["overall_quality"] == "STOP"

    def test_dissent_count(self):
        b = TumorBoard("P-200")
        b.add(Opinion("د. أ", "oncologist", "PROCEED", 0.9))
        b.add(Opinion("د. ب", "physicist", "PROCEED", 0.8))
        b.add(Opinion("د. ج", "surgeon", "REVIEW", 0.7))
        r = combine(make_report(), b.decide())
        assert r["synthesis"]["board_dissent"] == 1
