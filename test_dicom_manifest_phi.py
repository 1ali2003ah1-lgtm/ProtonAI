"""P1-S4: manifest build + PHI sweep on the ingestion path (ADR-001).

Pipeline under test:
    synthetic DICOM slices -> DicomReader -> records -> manifest.json
    -> DatasetLoader.load -> records -> phi_scrubber sweep

Safety linkage: RSK-001 R-004 (no real PHI may leave the ingestion path).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from dataset_loader import DatasetLoader
from dicom_reader import DicomReader
import phi_scrubber

SERIES = Path("data/synth_ct/SYNTH-001")
KEYS = ["PatientID", "Modality", "StudyInstanceUID"]

RICH_PHI = (
    "Patient: Smith, John; DOB 1980-01-01; email john.smith@hospital.org; "
    "phone +1-555-0100; MRN 123456; address 12 Main St, Springfield"
)


def _build_records():
    reader = DicomReader(metadata_keys=KEYS)
    records = []
    for path in sorted(SERIES.glob("*.dcm")):
        out = reader.read(path)
        meta = out["metadata"]
        records.append(
            {
                "slice_id": path.name,
                "patient_id": meta["PatientID"],
                "modality": meta["Modality"],
                "min_hu": out["min"],
                "max_hu": out["max"],
            }
        )
    return records


@pytest.fixture(scope="module")
def manifest_records(tmp_path_factory):
    records = _build_records()
    manifest = tmp_path_factory.mktemp("manifest") / "manifest.json"
    manifest.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
    loader = DatasetLoader(
        feature_columns=["min_hu", "max_hu"],
        target_column="patient_id",
        missing_strategy="fill_mean",
    )
    return loader, loader.load(manifest), records


def test_manifest_roundtrip(manifest_records):
    _, loaded, original = manifest_records
    assert len(loaded) == len(original) == 8
    assert [r["slice_id"] for r in loaded] == [r["slice_id"] for r in original]


def test_summary_columns_found(manifest_records):
    loader, loaded, _ = manifest_records
    summary = loader.summary(loaded)
    assert summary["columns_found"] == sorted(loaded[0].keys())


def test_load_rejects_unsupported_extension(tmp_path):
    bad = tmp_path / "manifest.txt"
    bad.write_text("x", encoding="utf-8")
    loader = DatasetLoader(
        feature_columns=["min_hu"],
        target_column="patient_id",
        missing_strategy="fill_mean",
    )
    with pytest.raises(ValueError):
        loader.load(bad)


def test_loader_rejects_empty_feature_columns():
    with pytest.raises(ValueError):
        DatasetLoader(
            feature_columns=[],
            target_column="patient_id",
            missing_strategy="fill_mean",
        )


def test_phi_detector_positive_control():
    assert not phi_scrubber.is_clean(RICH_PHI), "PHI detector is a no-op"


def test_phi_sweep_manifest_clean(manifest_records):
    _, loaded, _ = manifest_records
    violations = [
        (key, value)
        for rec in loaded
        for key, value in rec.items()
        if isinstance(value, str) and not phi_scrubber.is_clean(value)
    ]
    assert not violations, f"PHI flags in manifest: {violations}"
