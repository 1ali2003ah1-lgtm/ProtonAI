"""
ProtonAI - Test Experiment Tracker
اختبارات متتبّع التجارب وتثبيت التقسيمات
"""

import pytest
from experiment_tracker import ExperimentTracker, fingerprint, stable_split


def _data():
    return [{"a": 1, "b": 2}, {"a": 3, "b": 4}]


class TestFingerprint:
    def test_deterministic(self):
        assert fingerprint(_data()) == fingerprint(_data())

    def test_key_order_independent(self):
        assert fingerprint({"a": 1, "b": 2}) == fingerprint({"b": 2, "a": 1})

    def test_different_data_different_fp(self):
        assert fingerprint(_data()) != fingerprint([{"a": 99}])

    def test_length_64(self):
        assert len(fingerprint(_data())) == 64


class TestStableSplit:
    def test_deterministic(self):
        d = _data() * 10
        t1, e1, fp1 = stable_split(d, 0.8, 42)
        t2, e2, fp2 = stable_split(d, 0.8, 42)
        assert t1 == t2 and e1 == e2 and fp1 == fp2

    def test_different_seed_different_split(self):
        d = _data() * 10
        _, _, fp1 = stable_split(d, 0.8, 1)
        _, _, fp2 = stable_split(d, 0.8, 2)
        assert fp1 != fp2

    def test_sizes(self):
        d = [{"x": i} for i in range(100)]
        t, e, _ = stable_split(d, 0.7, 42)
        assert len(t) == 70 and len(e) == 30

    def test_invalid_ratio_raises(self):
        with pytest.raises(ValueError):
            stable_split(_data(), 1.5)


class TestRegister:
    def test_register_adds(self):
        tr = ExperimentTracker()
        e = tr.register("exp1", {"lr": 0.01}, _data(), metrics={"acc": 0.9})
        assert len(tr.experiments) == 1
        assert e.name == "exp1"
        assert e.metrics["acc"] == 0.9
        assert len(e.experiment_id) == 12

    def test_data_fingerprint_stored(self):
        tr = ExperimentTracker()
        e = tr.register("x", {}, _data())
        assert e.data_fingerprint == fingerprint(_data())


class TestVerify:
    def test_verify_same_data(self):
        tr = ExperimentTracker()
        e = tr.register("x", {}, _data())
        assert tr.verify(e.experiment_id, _data()) is True

    def test_verify_changed_data(self):
        tr = ExperimentTracker()
        e = tr.register("x", {}, _data())
        assert tr.verify(e.experiment_id, [{"a": 99}]) is False

    def test_verify_split_mismatch(self):
        tr = ExperimentTracker()
        e = tr.register("x", {}, _data(), split_fingerprint="aaa")
        assert tr.verify(e.experiment_id, _data(), split_fingerprint="bbb") is False

    def test_verify_unknown_id(self):
        assert ExperimentTracker().verify("nope", _data()) is False


class TestQueries:
    def test_find_by_data(self):
        tr = ExperimentTracker()
        tr.register("a", {}, _data())
        tr.register("b", {}, [{"z": 1}])
        assert len(tr.find_by_data(_data())) == 1

    def test_best_higher(self):
        tr = ExperimentTracker()
        tr.register("a", {}, _data(), metrics={"acc": 0.8})
        tr.register("b", {}, _data(), metrics={"acc": 0.95})
        assert tr.best("acc").name == "b"

    def test_best_lower(self):
        tr = ExperimentTracker()
        tr.register("a", {}, _data(), metrics={"mae": 1.5})
        tr.register("b", {}, _data(), metrics={"mae": 0.7})
        assert tr.best("mae", higher_better=False).name == "b"

    def test_best_no_candidate(self):
        tr = ExperimentTracker()
        tr.register("a", {}, _data(), metrics={"acc": 0.9})
        assert tr.best("missing") is None

    def test_list_all(self):
        tr = ExperimentTracker()
        tr.register("a", {}, _data())
        tr.register("b", {}, _data())
        assert len(tr.list_all()) == 2


class TestPersistence:
    def test_save_load(self, tmp_path):
        tr = ExperimentTracker()
        tr.register("x", {"lr": 0.1}, _data(), metrics={"acc": 0.9}, notes="hi")
        p = tmp_path / "exp.json"
        tr.save(p)
        tr2 = ExperimentTracker()
        tr2.load(p)
        assert len(tr2.experiments) == 1
        assert tr2.experiments[0].notes == "hi"
        assert tr2.experiments[0].config["lr"] == 0.1

    def test_load_missing_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            ExperimentTracker().load(tmp_path / "nope.json")
