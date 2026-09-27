"""P3-S2: real-data adapter privacy gate, tested in both directions."""
from __future__ import annotations

import shutil
from pathlib import Path

import pydicom
import pytest

from real_data_adapter import (PrivacyGateError, deid_report,
                               ingest_real_series, scan_dicom_dir)

SRC = Path("data/synth_ct/SYNTH-002")


@pytest.fixture()
def clean_series(tmp_path):
    dst = tmp_path / "clean"
    shutil.copytree(SRC, dst, ignore=shutil.ignore_patterns("ground_truth"))
    return dst


@pytest.fixture()
def phi_series(tmp_path):
    dst = tmp_path / "phi"
    shutil.copytree(SRC, dst, ignore=shutil.ignore_patterns("ground_truth"))
    for f in sorted(dst.glob("*.dcm")):
        ds = pydicom.dcmread(str(f))
        ds.PatientName = "Smith^John DOB 1980-01-01 MRN 123456"
        ds.PatientID = "MRN-123456"
        ds.save_as(str(f), write_like_original=False)
    return dst


def test_scan_finds_slices(clean_series):
    assert len(scan_dicom_dir(clean_series)) == 8


def test_deid_report_lists_fields(clean_series):
    rep = deid_report(clean_series)
    assert len(rep) == 8
    assert all("PatientID" in r for r in rep)


def test_gate_refuses_identifiable_data(phi_series):
    with pytest.raises(PrivacyGateError):
        ingest_real_series(phi_series)


def test_gate_accepts_clean_synthetic(clean_series):
    records = ingest_real_series(clean_series)
    assert len(records) == 8
    assert all("min_hu" in r and "max_hu" in r for r in records)


def test_allow_phi_override_documented(phi_series):
    records = ingest_real_series(phi_series, allow_phi=True)
    assert len(records) == 8
