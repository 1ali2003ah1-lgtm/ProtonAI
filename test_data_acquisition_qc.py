"""P4-S3: acquisition QC gate behavior guard (3 decisions)."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pydicom
import pytest

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "tools"))

from run_data_acquisition_qc import run_checks  # noqa: E402

SRC = ROOT / "data" / "synth_ct" / "SYNTH-002"


@pytest.fixture()
def clean_series(tmp_path):
    dst = tmp_path / "clean"
    shutil.copytree(SRC, dst)
    return dst


@pytest.fixture()
def phi_series(tmp_path):
    dst = tmp_path / "phi"
    shutil.copytree(SRC, dst)
    for f in sorted(dst.glob("*.dcm")):
        ds = pydicom.dcmread(str(f))
        ds.PatientName = "Smith^John DOB 1980-01-01 MRN 123456"
        try:
            pydicom.dcmwrite(str(f), ds, enforce_file_format=True)
        except TypeError:
            ds.save_as(str(f), write_like_original=False)
    return dst


@pytest.fixture()
def incomplete_series(tmp_path):
    dst = tmp_path / "incomplete"
    shutil.copytree(SRC, dst)
    for f in sorted(dst.glob("*.dcm"))[4:]:
        f.unlink()
    return dst


def test_accept_clean(clean_series):
    checks, decision = run_checks(clean_series)
    assert decision == "ACCEPT"
    assert checks["deid_gate"] == "PASS"


def test_reject_phi(phi_series):
    checks, decision = run_checks(phi_series)
    assert decision == "REJECT"
    assert checks["deid_gate"] == "FAIL"


def test_reject_incomplete(incomplete_series):
    checks, decision = run_checks(incomplete_series)
    assert decision == "REJECT"
    assert checks["completeness"].startswith("FAIL")
