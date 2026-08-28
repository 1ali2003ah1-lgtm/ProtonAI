"""
ProtonAI - Test Cohort Analytics
"""

import pytest
from case_orchestrator import CaseOrchestrator, CaseSpec
from cohort_analytics import analyze, render_text


def make(case, status="GREEN"):
    return CaseOrchestrator().run(CaseSpec(case, "prostate", status=status))


class TestAnalyze:
    def test_counts(self):
        ds = [make("P-1"), make("P-2"), make("P-3", status="RED")]
        st = analyze(ds)
        assert st.total == 3 and st.valid == 3
        assert st.decision_counts["STOP"] == 1
        assert st.stop_rate == pytest.approx(1 / 3, abs=0.01)

    def test_invalid_excluded(self):
        d = make("P-4")
        d.stages[0].summary = "tampered"
        st = analyze([d, make("P-5")])
        assert st.invalid == 1 and st.valid == 1

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            analyze([])

    def test_by_site(self):
        st = analyze([make("P-6")])
        assert "prostate" in st.by_site


class TestRender:
    def test_text(self):
        st = analyze([make("P-7")])
        assert "cohort" in render_text(st)
