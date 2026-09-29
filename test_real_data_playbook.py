"""P6-S3: playbook orchestration guard (4 tests)."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pydicom
import pytest

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "tools"))

from run_real_data_playbook import run_playbook  # noqa: E402

SRC = ROOT / "data" / "synth_ct" / "SYNTH-002"


def _paths(tmp):
    return dict(register=tmp / "reg.md", report_dir=tmp, seal_dir=tmp,
                audit_path=tmp / "audit.json", summary_path=tmp / "sum.json",
                out_path=tmp / "playbook.json")


@pytest.fixture()
def clean(tmp_path):
    d = tmp_path / "clean"
    shutil.copytree(SRC, d)
    return tmp_path, d


@pytest.fixture()
def phi(tmp_path):
    d = tmp_path / "phi"
    shutil.copytree(SRC, d)
    for f in sorted(d.glob("*.dcm")):
        ds = pydicom.dcmread(str(f))
        ds.PatientName = "Smith^John DOB 1980-01-01 MRN 123456"
        ds.PatientID = "MRN-123456"
        try:
            pydicom.dcmwrite(str(f), ds, enforce_file_format=True)
        except TypeError:
            ds.save_as(str(f), write_like_original=False)
    return tmp_path, d


def test_full_run_accept_and_validate(clean):
    tmp, d = clean
    r = run_playbook(d, "PB-CLEAN", **_paths(tmp))
    assert r["intake_decision"] == "ACCEPT"
    assert r["validation"] is not None
    assert 0.0 <= r["validation"]["wilcoxon_p"] <= 1.0
    assert (tmp / "PROVENANCE_PB-CLEAN.json").exists()
    assert (tmp / "playbook.json").exists()


def test_phi_reject_halts_chain(phi):
    tmp, d = phi
    r = run_playbook(d, "PB-PHI", **_paths(tmp))
    assert r["intake_decision"] == "REJECT"
    assert r["validation"] is None
    assert not (tmp / "PROVENANCE_PB-PHI.json").exists()


def test_dry_run_no_side_effects(clean):
    tmp, d = clean
    run_playbook(d, "PB-DRY", dry_run=True, **_paths(tmp))
    assert not (tmp / "reg.md").exists()
    assert not (tmp / "playbook.json").exists()
    assert not list(tmp.glob("PROVENANCE_*"))


def test_playbook_artifact_consistent(clean):
    tmp, d = clean
    run_playbook(d, "PB-CONS", **_paths(tmp))
    a = json.loads((tmp / "playbook.json").read_text(encoding="utf-8"))
    assert a["intake_decision"] == "ACCEPT"
    assert a["validation"]["seal_intact"] is True
