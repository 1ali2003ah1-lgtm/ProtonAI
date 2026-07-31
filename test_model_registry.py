"""
ProtonAI - Test Model Registry
اختبارات مكتبة النماذج المؤرشفة
"""

import pytest
from model_registry import ModelRegistry, ModelEntry, ModelStatus
from generic_model import GenericModel
from audit import AuditTrail


def _data():
    return [{"f1": i, "f2": i * 2, "label": "M" if i > 20 else "B"} for i in range(40)]


def _trained(est=10, seed=1):
    m = GenericModel(["f1", "f2"], "label", n_estimators=est, random_seed=seed)
    m.fit(_data())
    return m


@pytest.fixture
def reg(tmp_path):
    return ModelRegistry(tmp_path / "reg")


class TestRegister:
    def test_first_version_is_one(self, reg):
        e = reg.register("lung", _trained())
        assert e.version == 1
        assert len(e.model_id) == 12
        assert e.status == ModelStatus.ACTIVE

    def test_version_increments_per_name(self, reg):
        reg.register("lung", _trained())
        e2 = reg.register("lung", _trained(seed=2))
        assert e2.version == 2

    def test_different_names_independent_versions(self, reg):
        reg.register("lung", _trained())
        e = reg.register("brain", _trained())
        assert e.version == 1

    def test_model_file_created(self, reg):
        e = reg.register("lung", _trained())
        assert (reg.models_dir / e.model_path).exists()

    def test_metadata_stored(self, reg):
        e = reg.register("lung", _trained(), metrics={"accuracy": 0.9},
                         data_fingerprint="abc", experiment_id="exp1",
                         tags=["v1", "rf"], notes="hi")
        assert e.metrics["accuracy"] == 0.9
        assert e.data_fingerprint == "abc"
        assert e.experiment_id == "exp1"
        assert e.tags == ["v1", "rf"]
        assert e.notes == "hi"

    def test_untrained_model_raises(self, reg):
        m = GenericModel(["f1", "f2"], "label")  # لم يُدرّب
        with pytest.raises(RuntimeError):
            reg.register("lung", m)


class TestGet:
    def test_get_by_id(self, reg):
        e = reg.register("lung", _trained())
        assert reg.get(e.model_id).model_id == e.model_id

    def test_get_unknown_raises(self, reg):
        with pytest.raises(ValueError):
            reg.get("nope")

    def test_get_by_version(self, reg):
        reg.register("lung", _trained())
        e2 = reg.register("lung", _trained(seed=2))
        assert reg.get_by_version("lung", 2).model_id == e2.model_id

    def test_get_by_version_unknown_raises(self, reg):
        reg.register("lung", _trained())
        with pytest.raises(ValueError):
            reg.get_by_version("lung", 99)


class TestLoadModel:
    def test_load_predicts_same(self, reg):
        m = _trained()
        e = reg.register("lung", m)
        loaded = reg.load_model(e.model_id)
        assert loaded.predict(_data()[:3]) == m.predict(_data()[:3])

    def test_load_unknown_raises(self, reg):
        with pytest.raises(ValueError):
            reg.load_model("nope")

    def test_load_missing_file_raises(self, reg):
        e = reg.register("lung", _trained())
        (reg.models_dir / e.model_path).unlink()  # حذف الملف يدوياً
        with pytest.raises(FileNotFoundError):
            reg.load_model(e.model_id)


class TestList:
    def test_list_all(self, reg):
        reg.register("lung", _trained())
        reg.register("brain", _trained())
        assert len(reg.list_all()) == 2

    def test_list_by_name(self, reg):
        reg.register("lung", _trained())
        reg.register("lung", _trained(seed=2))
        reg.register("brain", _trained())
        assert len(reg.list_by_name("lung")) == 2

    def test_list_by_status(self, reg):
        e = reg.register("lung", _trained())
        reg.promote(e.model_id)
        assert len(reg.list_by_status(ModelStatus.PRODUCTION)) == 1
        assert len(reg.list_by_status(ModelStatus.ACTIVE)) == 0


class TestPromote:
    def test_promote_sets_production(self, reg):
        e = reg.register("lung", _trained())
        reg.promote(e.model_id)
        assert reg.get(e.model_id).status == ModelStatus.PRODUCTION

    def test_promote_replaces_old_production(self, reg):
        e1 = reg.register("lung", _trained())
        e2 = reg.register("lung", _trained(seed=2))
        reg.promote(e1.model_id)
        reg.promote(e2.model_id)
        assert reg.get(e1.model_id).status == ModelStatus.ACTIVE
        assert reg.get(e2.model_id).status == ModelStatus.PRODUCTION

    def test_promote_archived_raises(self, reg):
        e = reg.register("lung", _trained())
        reg.archive(e.model_id)
        with pytest.raises(ValueError):
            reg.promote(e.model_id)

    def test_promote_unknown_raises(self, reg):
        with pytest.raises(ValueError):
            reg.promote("nope")


class TestArchive:
    def test_archive_sets_status(self, reg):
        e = reg.register("lung", _trained())
        reg.archive(e.model_id)
        assert reg.get(e.model_id).status == ModelStatus.ARCHIVED

    def test_archived_excluded_from_best(self, reg):
        e1 = reg.register("lung", _trained(), metrics={"accuracy": 0.99})
        e2 = reg.register("lung", _trained(seed=2), metrics={"accuracy": 0.5})
        reg.archive(e1.model_id)
        best = reg.best("lung", "accuracy")
        assert best.model_id == e2.model_id


class TestBest:
    def test_best_higher(self, reg):
        reg.register("lung", _trained(), metrics={"accuracy": 0.8})
        e2 = reg.register("lung", _trained(seed=2), metrics={"accuracy": 0.95})
        assert reg.best("lung", "accuracy").model_id == e2.model_id

    def test_best_lower(self, reg):
        reg.register("lung", _trained(), metrics={"mae": 1.5})
        e2 = reg.register("lung", _trained(seed=2), metrics={"mae": 0.7})
        assert reg.best("lung", "mae", higher_better=False).model_id == e2.model_id

    def test_best_none_when_no_metric(self, reg):
        reg.register("lung", _trained(), metrics={"accuracy": 0.9})
        assert reg.best("lung", "missing") is None

    def test_best_none_when_empty(self, reg):
        assert reg.best("lung", "accuracy") is None


class TestPersistence:
    def test_save_load_metadata(self, reg, tmp_path):
        reg.register("lung", _trained(), metrics={"accuracy": 0.9}, notes="x")
        p = tmp_path / "reg.json"
        reg.save(p)
        reg2 = ModelRegistry(tmp_path / "reg2")
        reg2.load(p)
        assert len(reg2.entries) == 1
        assert reg2.entries[0].notes == "x"
        assert reg2.entries[0].metrics["accuracy"] == 0.9

    def test_default_path(self, reg):
        reg.register("lung", _trained())
        reg.save()
        assert (reg.store_dir / "registry.json").exists()

    def test_load_missing_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            ModelRegistry(tmp_path / "r").load(tmp_path / "nope.json")


class TestSummary:
    def test_summary_keys(self, reg):
        reg.register("lung", _trained())
        reg.register("lung", _trained(seed=2))
        s = reg.summary()
        assert s["total"] == 2
        assert s["by_name"]["lung"] == 2
        assert s["by_status"]["active"] == 2


class TestAudit:
    def test_register_and_promote_logged(self, tmp_path):
        audit = AuditTrail()
        reg = ModelRegistry(tmp_path / "r", audit=audit)
        e = reg.register("lung", _trained())
        reg.promote(e.model_id)
        actions = [ev.action for ev in audit.events]
        assert "register" in actions
        assert "promote" in actions
        assert audit.verify_chain() is True
