"""
ProtonAI - Test SaMD Classification
"""

from samd_classifier import (fda_class, mdr_class, iec_62304_class,
                             classification_summary)


class TestFda:
    def test_cdss_is_class_2(self):
        assert fda_class() == "Class II"

    def test_direct_is_class_3(self):
        assert fda_class(direct_treatment=True) == "Class III"


class TestMdr:
    def test_default_2b(self):
        assert mdr_class() == "Class IIb"

    def test_critical_3(self):
        assert mdr_class(critical=True) == "Class III"

    def test_low_2a(self):
        assert mdr_class(serious=False) == "Class IIa"


class TestIec:
    def test_default_b(self):
        assert iec_62304_class() == "Class B"

    def test_death_c(self):
        assert iec_62304_class(death_possible=True) == "Class C"


class TestSummary:
    def test_all_keys(self):
        s = classification_summary()
        assert {"FDA", "EU_MDR", "IEC_62304", "rationale"} <= set(s.keys())
