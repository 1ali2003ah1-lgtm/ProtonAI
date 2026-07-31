"""
ProtonAI - Test Versioned Model Link
اختبارات ربط النماذج بالتجارب وسلسلة الإثبات
"""

import pytest
from versioned_model_link import VersionedModelLink, LinkRecord, CheckResult
from model_registry import ModelRegistry
from experiment_tracker import ExperimentTracker, fingerprint
from generic_model import GenericModel


def _data_a():
    return [{"f1": i, "f2": i * 2, "label": "M" if i > 20 else "B"} for i in range(40)]


def _data_b():
    return [{"f1": i + 1000, "f2": i, "label": "B"} for i in range(40)]


def _trained(seed=1):
    m = GenericModel(["f1", "f2"], "label", n_estimators=10, random_seed=seed)
    m.fit(_data_a())
    return m


@pytest.fixture
def setup(tmp_path):
    reg = ModelRegistry(tmp_path / "reg")
    trk = ExperimentTracker()
    link = VersionedModelLink(reg, trk)
    return reg, trk, link


class TestLink:
    def test_link_fills_data_fingerprint(self, setup):
        reg, trk, link = setup
        e = reg.register("lung", _trained())
        rec = link.link(e.model_id, data=_data_a())
        assert rec.data_fingerprint == fingerprint(_data_a())
        assert rec.verified is True

    def test_link_fills_experiment_id(self, setup):
        reg, trk, link = setup
        e = reg.register("lung", _trained())
        exp = trk.register("exp1", {}, _data_a(), metrics={"accuracy": 0.9})
        rec = link.link(e.model_id, experiment_id=exp.experiment_id)
        assert rec.experiment_id == exp.experiment_id
        assert rec.split_fingerprint == exp.split_fingerprint

    def test_link_fills_fp_from_experiment_when_missing(self, setup):
        reg, trk, link = setup
        e = reg.register("lung", _trained())  # data_fingerprint فاضي
        exp = trk.register("exp1", {}, _data_a())
        rec = link.link(e.model_id, experiment_id=exp.experiment_id)
        assert rec.data_fingerprint == exp.data_fingerprint

    def test_link_conflict_data_unverified(self, setup):
        reg, trk, link = setup
        e = reg.register("lung", _trained(), data_fingerprint=fingerprint(_data_a()))
        # نمرر بيانات مختلفة → تعارض
        rec = link.link(e.model_id, data=_data_b())
        assert rec.verified is False

    def test_link_conflict_model_experiment_unverified(self, setup):
        reg, trk, link = setup
        # نموذج على data_a، تجربة على data_b
        e = reg.register("lung", _trained(), data_fingerprint=fingerprint(_data_a()))
        exp = trk.register("exp1", {}, _data_b())
        rec = link.link(e.model_id, experiment_id=exp.experiment_id)
        assert rec.verified is False

    def test_link_consistent_verified(self, setup):
        reg, trk, link = setup
        e = reg.register("lung", _trained(), data_fingerprint=fingerprint(_data_a()))
        exp = trk.register("exp1", {}, _data_a(), split_fingerprint="sp1")
        rec = link.link(e.model_id, experiment_id=exp.experiment_id, data=_data_a())
        assert rec.verified is True
        assert rec.split_fingerprint == "sp1"

    def test_link_record_fields(self, setup):
        reg, trk, link = setup
        e = reg.register("lung", _trained(), metrics={"accuracy": 0.9})
        rec = link.link(e.model_id, data=_data_a())
        assert rec.name == "lung"
        assert rec.version == 1
        assert rec.metrics["accuracy"] == 0.9
        assert isinstance(rec, LinkRecord)

    def test_link_unknown_raises(self, setup):
        _, _, link = setup
        with pytest.raises(ValueError):
            link.link("nope")


class TestVerify:
    def test_verify_data_match(self, setup):
        reg, trk, link = setup
        e = reg.register("lung", _trained(), data_fingerprint=fingerprint(_data_a()))
        res = link.verify(e.model_id, data=_data_a())
        assert res["valid"] is True
        assert all(c["passed"] for c in res["checks"])

    def test_verify_data_mismatch(self, setup):
        reg, trk, link = setup
        e = reg.register("lung", _trained(), data_fingerprint=fingerprint(_data_a()))
        res = link.verify(e.model_id, data=_data_b())
        assert res["valid"] is False
        names = [c["name"] for c in res["checks"]]
        assert "data_fingerprint" in names

    def test_verify_experiment_match(self, setup):
        reg, trk, link = setup
        e = reg.register("lung", _trained())
        exp = trk.register("exp1", {}, _data_a())
        link.link(e.model_id, experiment_id=exp.experiment_id, data=_data_a())
        res = link.verify(e.model_id, experiment_id=exp.experiment_id)
        assert res["valid"] is True

    def test_verify_experiment_mismatch(self, setup):
        reg, trk, link = setup
        e = reg.register("lung", _trained())
        exp = trk.register("exp1", {}, _data_a())
        link.link(e.model_id, experiment_id=exp.experiment_id)
        res = link.verify(e.model_id, experiment_id="wrong_id")
        assert res["valid"] is False

    def test_verify_split_match(self, setup):
        reg, trk, link = setup
        e = reg.register("lung", _trained())
        exp = trk.register("exp1", {}, _data_a(), split_fingerprint="spX")
        link.link(e.model_id, experiment_id=exp.experiment_id)
        res = link.verify(e.model_id, split_fp="spX")
        assert res["valid"] is True

    def test_verify_split_mismatch(self, setup):
        reg, trk, link = setup
        e = reg.register("lung", _trained())
        exp = trk.register("exp1", {}, _data_a(), split_fingerprint="spX")
        link.link(e.model_id, experiment_id=exp.experiment_id)
        res = link.verify(e.model_id, split_fp="wrong")
        assert res["valid"] is False

    def test_verify_no_checks_is_valid(self, setup):
        reg, trk, link = setup
        e = reg.register("lung", _trained())
        res = link.verify(e.model_id)  # بلا مدخلات → لا فحوص → valid
        assert res["valid"] is True
        assert res["checks"] == []

    def test_verify_unknown_raises(self, setup):
        _, _, link = setup
        with pytest.raises(ValueError):
            link.verify("nope")


class TestLineage:
    def test_lineage_with_experiment(self, setup):
        reg, trk, link = setup
        e = reg.register("lung", _trained(), metrics={"accuracy": 0.9})
        exp = trk.register("exp1", {"seed": 1}, _data_a(), metrics={"accuracy": 0.9})
        link.link(e.model_id, experiment_id=exp.experiment_id, data=_data_a())
        lin = link.lineage(e.model_id)
        assert lin["model"]["name"] == "lung"
        assert lin["model"]["metrics"]["accuracy"] == 0.9
        assert lin["experiment"]["experiment_id"] == exp.experiment_id
        assert lin["experiment"]["split_fingerprint"] == exp.split_fingerprint
        assert lin["data_fingerprint"] == fingerprint(_data_a())

    def test_lineage_without_experiment(self, setup):
        reg, trk, link = setup
        e = reg.register("lung", _trained())
        link.link(e.model_id, data=_data_a())
        lin = link.lineage(e.model_id)
        assert "experiment" not in lin
        assert lin["data_fingerprint"] == fingerprint(_data_a())

    def test_lineage_unknown_raises(self, setup):
        _, _, link = setup
        with pytest.raises(ValueError):
            link.lineage("nope")


class TestFind:
    def test_find_by_experiment(self, setup):
        reg, trk, link = setup
        e1 = reg.register("lung", _trained())
        e2 = reg.register("brain", _trained(seed=2))
        exp = trk.register("exp1", {}, _data_a())
        link.link(e1.model_id, experiment_id=exp.experiment_id)
        found = link.find_by_experiment(exp.experiment_id)
        assert len(found) == 1
        assert found[0].model_id == e1.model_id

    def test_find_by_data(self, setup):
        reg, trk, link = setup
        e1 = reg.register("lung", _trained(), data_fingerprint=fingerprint(_data_a()))
        reg.register("brain", _trained(seed=2), data_fingerprint=fingerprint(_data_b()))
        found = link.find_by_data(_data_a())
        assert len(found) == 1
        assert found[0].model_id == e1.model_id

    def test_find_by_data_none(self, setup):
        reg, trk, link = setup
        reg.register("lung", _trained(), data_fingerprint=fingerprint(_data_a()))
        assert link.find_by_data(_data_b()) == []


class TestNoTracker:
    def test_link_without_tracker(self, tmp_path):
        reg = ModelRegistry(tmp_path / "reg")
        link = VersionedModelLink(reg, tracker=None)
        e = reg.register("lung", _trained())
        rec = link.link(e.model_id, data=_data_a())
        assert rec.data_fingerprint == fingerprint(_data_a())
        assert rec.split_fingerprint == ""
        assert rec.verified is True

    def test_verify_split_ignored_without_tracker(self, tmp_path):
        reg = ModelRegistry(tmp_path / "reg")
        link = VersionedModelLink(reg, tracker=None)
        e = reg.register("lung", _trained())
        res = link.verify(e.model_id, split_fp="anything")
        # بدون tracker، فحص الـ split يقارن بـ "" → يفشل
        assert res["valid"] is False
