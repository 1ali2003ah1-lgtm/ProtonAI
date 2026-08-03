"""
ProtonAI - Test External Test Sets
اختبارات التعميم الخارجي (دقة + فجوة + حكم + CI + نشر + حراس)
"""

import pytest
from external_test_sets import ExternalTestEvaluator, accuracy, _ci


def _lists(n, n_correct):
    """(y_true, y_pred): أول n_correct مطابقة والباقي خطأ"""
    y_true = ["A"] * n
    y_pred = ["A"] * n_correct + ["B"] * (n - n_correct)
    return y_true, y_pred


@pytest.fixture
def ev():
    return ExternalTestEvaluator()


class TestAccuracy:
    def test_perfect(self):
        t, p = _lists(10, 10)
        assert accuracy(t, p) == 1.0

    def test_partial(self):
        t, p = _lists(10, 7)
        assert accuracy(t, p) == pytest.approx(0.7)

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            accuracy([], [])

    def test_length_mismatch_raises(self):
        with pytest.raises(ValueError):
            accuracy(["A", "B"], ["A"])


class TestCI:
    def test_bounds(self):
        lo, hi = _ci(0.9, 50)
        assert lo <= 0.9 <= hi

    def test_width_positive(self):
        lo, hi = _ci(0.9, 50)
        assert hi > lo

    def test_zero_n(self):
        assert _ci(0.5, 0) == (0.5, 0.5)


class TestVerdict:
    def test_robust(self, ev):
        assert ev.verdict(0.02) == "robust"

    def test_robust_at_threshold(self, ev):
        assert ev.verdict(0.05) == "robust"

    def test_moderate(self, ev):
        assert ev.verdict(0.10) == "moderate"

    def test_moderate_at_poor_threshold(self, ev):
        assert ev.verdict(0.15) == "moderate"

    def test_poor(self, ev):
        assert ev.verdict(0.20) == "poor"


class TestEvaluate:
    def test_robust_publication_ready(self, ev):
        it, ip = _lists(50, 45)   # 0.9
        et, ep = _lists(50, 44)   # 0.88
        r = ev.evaluate(it, ip, et, ep)
        assert r["verdict"] == "robust"
        assert r["external_acceptable"] is True
        assert r["publication_ready"] is True
        assert r["generalization_gap"] == pytest.approx(0.02)

    def test_poor_not_ready(self, ev):
        it, ip = _lists(50, 45)   # 0.9
        et, ep = _lists(50, 30)   # 0.6
        r = ev.evaluate(it, ip, et, ep)
        assert r["verdict"] == "poor"
        assert r["external_acceptable"] is False
        assert r["publication_ready"] is False

    def test_moderate_ready_when_floor_met(self, ev):
        it, ip = _lists(50, 45)   # 0.9
        et, ep = _lists(50, 37)   # 0.74
        r = ev.evaluate(it, ip, et, ep)
        assert r["verdict"] == "moderate"
        assert r["external_acceptable"] is True
        assert r["publication_ready"] is True

    def test_moderate_not_ready_when_floor_missed(self, ev):
        # فجوة متوسطة بس الخارجي تحت الحد → غير جاهز للنشر
        e = ExternalTestEvaluator(external_floor=0.8)
        it, ip = _lists(50, 45)   # 0.9
        et, ep = _lists(50, 37)   # 0.74
        r = e.evaluate(it, ip, et, ep)
        assert r["verdict"] == "moderate"
        assert r["external_acceptable"] is False
        assert r["publication_ready"] is False

    def test_ci_present(self, ev):
        it, ip = _lists(50, 45)
        et, ep = _lists(50, 44)
        r = ev.evaluate(it, ip, et, ep)
        assert r["internal_ci"][0] <= r["internal_accuracy"] <= r["internal_ci"][1]
        assert r["external_ci"][0] <= r["external_accuracy"] <= r["external_ci"][1]

    def test_counts(self, ev):
        it, ip = _lists(50, 45)
        et, ep = _lists(40, 30)
        r = ev.evaluate(it, ip, et, ep)
        assert r["n_internal"] == 50
        assert r["n_external"] == 40


class TestGuards:
    def test_invalid_threshold_order(self):
        with pytest.raises(ValueError):
            ExternalTestEvaluator(gap_threshold=0.2, poor_threshold=0.1)

    def test_invalid_floor(self):
        with pytest.raises(ValueError):
            ExternalTestEvaluator(external_floor=1.5)

    def test_mismatch_raises_in_evaluate(self, ev):
        with pytest.raises(ValueError):
            ev.evaluate(["A"], ["A", "B"], ["A"], ["A"])
