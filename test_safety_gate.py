"""
ProtonAI - Test Safety Gate
"""

from safety_gate import evaluate


class TestDecisions:
    def test_proceed_when_good(self):
        r = evaluate()
        assert r["decision"] == "PROCEED"
        assert r["reasons"] == []

    def test_red_stops(self):
        r = evaluate(status="RED")
        assert r["decision"] == "STOP"

    def test_low_dice_reviews(self):
        r = evaluate(dice=0.7)
        assert r["decision"] == "REVIEW"

    def test_high_ece_reviews(self):
        r = evaluate(ece=0.2)
        assert r["decision"] == "REVIEW"

    def test_amber_reviews(self):
        r = evaluate(status="AMBER")
        assert r["decision"] == "REVIEW"


class TestCdss:
    def test_human_ack_always(self):
        for s in ["GREEN", "AMBER", "RED"]:
            assert evaluate(status=s)["requires_human_ack"] is True
