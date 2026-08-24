"""
ProtonAI - Test Site-aware Decision
"""

from site_decision import site_thresholds, site_evaluate


class TestThresholds:
    def test_priority1_stricter(self):
        t1 = site_thresholds("CNS_brain_spine")
        t2 = site_thresholds("prostate")
        assert t1["dice"] > t2["dice"]
        assert t1["ece"] < t2["ece"]


class TestDecision:
    def test_pediatric_strict(self):
        # Dice 0.88 مقبول للبروستاتا لكن مراجعة لـ CNS
        assert site_evaluate("CNS_brain_spine", dice=0.88)["decision"] == "REVIEW"
        assert site_evaluate("prostate", dice=0.88)["decision"] == "PROCEED"

    def test_red_stops(self):
        assert site_evaluate("ocular", status="RED")["decision"] == "STOP"

    def test_human_ack(self):
        assert site_evaluate("head_neck")["requires_human_ack"] is True
