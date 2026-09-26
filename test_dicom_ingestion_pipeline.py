"""P1-S3: DICOM ingestion integration test (ADR-001).

Validates the ingestion path end-to-end on synthetic series SYNTH-001:
1. Every slice is recognized as DICOM.
2. read() honors its contracted keys.
3. HU round-trip integrity: pixels == rint(ground_truth) exactly, and
   |pixels - ground_truth| <= 0.5 (int16 quantization bound).
4. Rescale toggle behaves per DICOM semantics.
5. Metadata contract: requested keys + _path.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from dicom_reader import DicomReader

SERIES = Path("data/synth_ct/SYNTH-001")
GT = SERIES / "ground_truth"
KEYS = ["PatientID", "Modality", "StudyInstanceUID"]


def _slices():
    return sorted(SERIES.glob("*.dcm"))


@pytest.fixture(scope="module")
def reader():
    return DicomReader(metadata_keys=KEYS)


def test_series_present():
    assert len(_slices()) == 8, "synthetic series missing; run tools/make_synthetic_dicom.py"


def test_all_slices_recognized_as_dicom(reader):
    assert all(reader.is_dicom(p) for p in _slices())


def test_read_contract_keys(reader):
    out = reader.read(_slices()[0])
    assert set(out) == {"metadata", "pixels", "shape", "min", "max"}


def test_hu_roundtrip_integrity(reader):
    hu = np.load(GT / "hu.npy")
    slices = _slices()
    assert len(slices) == hu.shape[0]
    for z, path in enumerate(slices):
        out = reader.read(path)
        pixels = np.asarray(out["pixels"], dtype=float)
        assert pixels.shape == hu.shape[1:], f"slice {z} shape mismatch"
        assert np.array_equal(pixels, np.rint(hu[z])), f"slice {z} exact round-trip failed"
        assert np.max(np.abs(pixels - hu[z])) <= 0.5, f"slice {z} quantization bound violated"
        assert out["shape"] == list(pixels.shape)
        assert out["min"] == float(pixels.min())
        assert out["max"] == float(pixels.max())


def test_rescale_toggle(reader):
    hu = np.load(GT / "hu.npy")
    raw = np.asarray(reader.read(_slices()[0], apply_rescale=False)["pixels"], dtype=float)
    assert np.array_equal(raw, np.rint(hu[0]) + 1024.0)


def test_metadata_contract(reader):
    meta = reader.read(_slices()[0])["metadata"]
    assert meta.get("PatientID") == "SYNTH-001"
    assert meta.get("Modality") == "CT"
    assert meta.get("_path") == str(_slices()[0])
