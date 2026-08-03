"""
ProtonAI - Test Reproducibility Package
اختبارات حزمة التكرار (بذور + إصدارات + تشيكسام + verify + حفظ/تحميل)
"""

import hashlib
import json
import pytest
from reproducibility_package import ReproducibilityPackage


@pytest.fixture
def pkg():
    return ReproducibilityPackage()


class TestSeeds:
    def test_add_seed(self, pkg):
        pkg.add_seed(42)
        pkg.add_seed(7)
        assert pkg.seeds == [42, 7]

    def test_init_seeds(self):
        p = ReproducibilityPackage(seeds=[1, 2, 3])
        assert p.seeds == [1, 2, 3]

    def test_manifest_seeds(self, pkg):
        pkg.add_seed(42)
        assert pkg.build_manifest()["seeds"] == [42]


class TestVersions:
    def test_python_recorded(self, pkg):
        v = pkg.record_versions()
        assert "python" in v
        assert v["python"]

    def test_no_crash_on_missing_lib(self, pkg):
        # ما ينهار حتى لو مكتبة ناقصة
        pkg.record_versions()
        assert isinstance(pkg.versions, dict)


class TestChecksums:
    def test_bytes_checksum_matches_hashlib(self, pkg):
        h = pkg.add_bytes_checksum("data", b"hello")
        assert h == hashlib.sha256(b"hello").hexdigest()

    def test_file_checksum(self, pkg, tmp_path):
        f = tmp_path / "x.csv"
        f.write_bytes(b"1,2,3")
        h = pkg.add_file_checksum(f)
        assert pkg.checksums["x.csv"] == h

    def test_verify_file_true(self, pkg, tmp_path):
        f = tmp_path / "x.csv"
        f.write_bytes(b"1,2,3")
        pkg.add_file_checksum(f)
        assert pkg.verify_file(f) is True

    def test_verify_file_false_after_modify(self, pkg, tmp_path):
        f = tmp_path / "x.csv"
        f.write_bytes(b"1,2,3")
        pkg.add_file_checksum(f)
        f.write_bytes(b"9,9,9")  # تعديل → البصمة تتغير
        assert pkg.verify_file(f) is False

    def test_verify_file_unknown_name(self, pkg, tmp_path):
        f = tmp_path / "new.csv"
        f.write_bytes(b"x")
        assert pkg.verify_file(f) is False  # غير مسجلة

    def test_verify_all(self, pkg, tmp_path):
        a = tmp_path / "a.csv"; a.write_bytes(b"a")
        b = tmp_path / "b.csv"; b.write_bytes(b"b")
        pkg.add_file_checksum(a)
        pkg.add_file_checksum(b)
        b.write_bytes(b"changed")
        res = pkg.verify_all([a, b])
        assert res == {"a.csv": True, "b.csv": False}


class TestSaveLoad:
    def test_roundtrip(self, pkg, tmp_path):
        pkg.add_seed(42)
        pkg.add_bytes_checksum("d", b"data")
        pkg.record_versions()
        p = pkg.save(tmp_path / "repro.json")
        loaded = ReproducibilityPackage.load(p)
        assert loaded.seeds == [42]
        assert loaded.checksums == pkg.checksums
        assert loaded.versions == pkg.versions

    def test_saved_json_valid(self, pkg, tmp_path):
        pkg.add_seed(1)
        p = pkg.save(tmp_path / "r.json")
        d = json.loads(p.read_text(encoding="utf-8"))
        assert d["seeds"] == [1]
        assert "generated_at" in d

    def test_manifest_keys(self, pkg):
        m = pkg.build_manifest()
        for k in ["seeds", "versions", "checksums", "generated_at"]:
            assert k in m
