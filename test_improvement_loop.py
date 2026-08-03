"""
ProtonAI - Test Improvement Loop
اختبارات حلقة التحسين (تشخيص + ترتيب + تتبع نسخ)
"""

import pytest
from improvement_loop import ImprovementLoop


def _retro(acc=0.9, errors=None):
    return {"accuracy": acc, "n_errors": len(errors or []), "errors": errors or []}


@pytest.fixture
def loop():
    return ImprovementLoop()


class TestLowAccuracy:
    def test_triggers_below_threshold(self, loop):
        issues = loop.diagnose(_retro(0.5))
        assert any(i["type"] == "low_accuracy" for i in issues)

    def test_no_trigger_above(self, loop):
        assert not any(i["type"] == "low_accuracy" for i in loop.diagnose(_retro(0.9)))

    def test_severity_high(self, loop):
        i = loop.diagnose(_retro(0.5))[0]
        assert i["severity"] == "high"


class TestClassBias:
    def test_bias_detected(self, loop):
        errs = [{"actual": "M"}, {"actual": "M"}, {"actual": "B"}]
        issues = loop.diagnose(_retro(0.5, errs))
        bias = next(i for i in issues if i["type"] == "class_bias")
        assert bias["label"] == "M"
        assert "M" in bias["suggestion"]

    def test_no_bias_when_balanced(self, loop):
        errs = [{"actual": "M"}, {"actual": "B"}]  # متوازن → لا انحياز
        issues = loop.diagnose(_retro(0.5, errs))
        assert not any(i["type"] == "class_bias" for i in issues)

    def test_no_bias_when_no_errors(self, loop):
        assert not any(i["type"] == "class_bias"
                       for i in loop.diagnose(_retro(1.0, [])))


class TestExternal:
    def test_overfitting_on_poor(self, loop):
        issues = loop.diagnose(_retro(0.9), {"verdict": "poor",
                                             "external_acceptable": False})
        assert any(i["type"] == "overfitting" for i in issues)

    def test_weak_generalization_when_floor_missed(self, loop):
        issues = loop.diagnose(_retro(0.9), {"verdict": "moderate",
                                             "external_acceptable": False})
        assert any(i["type"] == "weak_generalization" for i in issues)

    def test_no_external_no_overfitting(self, loop):
        assert not any(i["type"] == "overfitting" for i in loop.diagnose(_retro(0.9)))

    def test_good_external_no_issue(self, loop):
        issues = loop.diagnose(_retro(0.9), {"verdict": "robust",
                                             "external_acceptable": True})
        assert issues == []


class TestOrdering:
    def test_high_first(self, loop):
        errs = [{"actual": "M"}, {"actual": "M"}]
        issues = loop.diagnose(_retro(0.5, errs), {"verdict": "poor",
                                                   "external_acceptable": False})
        severities = [i["severity"] for i in issues]
        assert severities == sorted(severities, key=lambda s: {"high": 0, "medium": 1}[s])


class TestIterations:
    def test_version_increments(self, loop):
        v1 = loop.record_iteration(loop.diagnose(_retro(0.5)))
        v2 = loop.record_iteration([])
        assert v1 == 1
        assert v2 == 2

    def test_history_stores(self, loop):
        loop.record_iteration([{"type": "low_accuracy"}], chosen=["tune"])
        h = loop.history()
        assert len(h) == 1
        assert h[0]["version"] == 1
        assert h[0]["chosen"] == ["tune"]
        assert h[0]["timestamp"]

    def test_history_empty(self, loop):
        assert loop.history() == []


class TestGuards:
    def test_invalid_accuracy_threshold(self):
        with pytest.raises(ValueError):
            ImprovementLoop(accuracy_threshold=1.5)

    def test_invalid_bias_ratio(self):
        with pytest.raises(ValueError):
            ImprovementLoop(bias_ratio=0)
