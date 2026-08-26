"""
ProtonAI - Test Clinical Intelligence
"""

import pytest
from clinical_intelligence import ClinicalIntelligence, IntelligenceReport


@pytest.fixture
def ci():
    return ClinicalIntelligence()


class TestSynthesis:
    def test_returns_report(self, ci):
        r = ci.synthesize("P-100", "prostate",
                          achieved_oars={"rectum_V70": 10})
        assert isinstance(r, IntelligenceReport)

    def test_all_sections_present(self, ci):
        r = ci.synthesize("P-101", "lung_pleura",
                          achieved_oars={"lung_V20": 20, "lung_MLD": 10})
        assert r.narrative and r.risks and r.evidence and r.views and r.synthesis

    def test_evidence_count(self, ci):
        r = ci.synthesize("P-102", "prostate",
                          achieved_oars={"rectum_V70": 10})
        assert r.synthesis["evidence_count"] >= 4

    def test_narrative_mentions_decision(self, ci):
        r = ci.synthesize("P-103", "prostate", dice=0.92, ece=0.02,
                          achieved_oars={"rectum_V70": 10})
        assert "PROCEED" in r.narrative or "REVIEW" in r.narrative


class TestRisks:
    def test_stop_adds_high_risk(self, ci):
        r = ci.synthesize("P-104", "CNS_brain_spine", status="RED",
                          achieved_oars={"cord_Dmax": 30})
        assert any(x.level == "HIGH" and x.domain == "operational" for x in r.risks)

    def test_oar_violation_adds_risk(self, ci):
        r = ci.synthesize("P-105", "prostate",
                          achieved_oars={"rectum_V70": 25})  # > 15
        assert any(x.domain == "clinical" for x in r.risks)


class TestViews:
    def test_four_views(self, ci):
        r = ci.synthesize("P-106", "prostate",
                          achieved_oars={"rectum_V70": 10})
        assert set(r.views.keys()) == {"physician", "physicist", "patient", "committee"}

    def test_patient_simple(self, ci):
        r = ci.synthesize("P-107", "prostate",
                          achieved_oars={"rectum_V70": 10})
        patient_view = r.views["patient"]
        assert any("أمان" in p for p in patient_view.key_points)


class TestEconomy:
    def test_cost_effective(self, ci):
        r = ci.synthesize("P-108", "prostate",
                          cost_proton=60000, cost_photon=50000,
                          qaly_p=8.2, qaly_f=7.8,
                          achieved_oars={"rectum_V70": 10})
        assert r.synthesis["cost_effective"] is True

    def test_not_cost_effective(self, ci):
        r = ci.synthesize("P-109", "prostate",
                          cost_proton=120000, cost_photon=50000,
                          qaly_p=8.2, qaly_f=7.8,
                          achieved_oars={"rectum_V70": 10})
        assert r.synthesis["cost_effective"] is False
