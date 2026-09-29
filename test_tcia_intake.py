"""P5-S3 hardened intake guard (6 tests)."""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

import pydicom
import pytest

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "tools"))

from run_tcia_intake import process_manifest  # noqa: E402

SRC = ROOT / "data" / "synth_ct" / "SYNTH-002"


@pytest.fixture()
def env(tmp_path):
    clean = tmp_path / "clean"
    shutil.copytree(SRC, clean)
    phi = tmp_path / "phi"
    shutil.copytree(SRC, phi)
    for f in sorted(phi.glob("*.dcm")):
        ds = pydicom.dcmread(str(f))
        ds.PatientName = "Smith^John DOB 1980-01-01 MRN 123456"
        ds.PatientID = "MRN-123456"
        try:
            pydicom.dcmwrite(str(f), ds, enforce_file_format=True)
        except TypeError:
            ds.save_as(str(f), write_like_original=False)
    inc = tmp_path / "inc"
    shutil.copytree(SRC, inc)
    for f in sorted(inc.glob("*.dcm"))[4:]:
        f.unlink()
    man = tmp_path / "manifest.json"
    man.write_text(json.dumps({"entries": [
        {"dataset_id": "T-CLEAN", "path": str(clean), "source": "test"},
        {"dataset_id": "T-PHI", "path": str(phi), "source": "test"},
        {"dataset_id": "T-INC", "path": str(inc), "source": "test"}]}))
    return tmp_path, man


def _run(tmp, man, **kw):
    return process_manifest(man, register=tmp / "reg.md", report_dir=tmp,
                            summary_path=tmp / "sum.json", seal_dir=tmp,
                            audit_path=tmp / "audit.json", **kw)


def test_decisions_and_selective_sealing(env):
    tmp, man = env
    s = _run(tmp, man)
    assert s["accept"] == 1 and s["reject"] == 2
    assert (tmp / "PROVENANCE_T-CLEAN.json").exists()
    assert not (tmp / "PROVENANCE_T-PHI.json").exists()
    assert not (tmp / "PROVENANCE_T-INC.json").exists()
    assert s["power_progress"]["n_min"] == 19


def test_audit_trail_hashes(env):
    tmp, man = env
    _run(tmp, man)
    audit = json.loads((tmp / "audit.json").read_text(encoding="utf-8"))
    assert len(audit) == 3
    for row in audit:
        rep = tmp / f"acquisition_qc_{row['dataset_id']}.json"
        assert row["qc_report_sha256"] == hashlib.sha256(
            rep.read_bytes()).hexdigest()


def test_dry_run_no_side_effects(env):
    tmp, man = env
    _run(tmp, man, dry_run=True)
    assert not (tmp / "reg.md").exists()
    assert not (tmp / "audit.json").exists()
    assert not list(tmp.glob("acquisition_qc_*"))
    assert not list(tmp.glob("PROVENANCE_*"))


def test_ledger_idempotent_audit_append_only(env):
    tmp, man = env
    _run(tmp, man)
    _run(tmp, man)
    reg = (tmp / "reg.md").read_text(encoding="utf-8")
    assert reg.count("| T-CLEAN |") == 1
    audit = json.loads((tmp / "audit.json").read_text(encoding="utf-8"))
    assert len(audit) == 6


def test_schema_problems_enumerated(tmp_path):
    bad = tmp_path / "m.json"
    bad.write_text(json.dumps({"entries": [
        {"dataset_id": "X", "path": "a"},
        {"dataset_id": "X", "path": "b"},
        {"dataset_id": "Y"}]}))
    with pytest.raises(SystemExit) as ei:
        process_manifest(bad, register=tmp_path / "r.md",
                         report_dir=tmp_path, summary_path=tmp_path / "s.json",
                         seal_dir=tmp_path, audit_path=tmp_path / "a.json")
    msg = str(ei.value)
    assert "duplicated" in msg and "missing path" in msg


def test_summary_written(env):
    tmp, man = env
    _run(tmp, man)
    s = json.loads((tmp / "sum.json").read_text(encoding="utf-8"))
    for k in ("processed", "accept", "reject", "power_progress", "entries"):
        assert k in s
