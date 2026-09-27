"""P3-S2: Real-world DICOM adapter with mandatory de-identification gate.

Real clinical data may only enter the ProtonAI pipeline after passing a
PHI sweep (phi_scrubber). Identifiable series are refused by default.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import phi_scrubber
from dicom_reader import DicomReader

PHI_TAGS = ["PatientName", "PatientID", "PatientBirthDate", "PatientAddress",
            "PatientTelephoneNumbers", "InstitutionName",
            "ReferringPhysicianName", "OperatorsName", "StudyDate",
            "AccessionNumber", "OtherPatientIDs"]
SWEEP_TAGS = ["PatientName", "PatientID", "OtherPatientIDs",
              "PatientAddress", "PatientTelephoneNumbers",
              "ReferringPhysicianName", "OperatorsName", "InstitutionName"]


class PrivacyGateError(RuntimeError):
    """Raised when identifiable real data attempts to enter the pipeline."""


def scan_dicom_dir(path) -> List[Path]:
    p = Path(path)
    if not p.is_dir():
        raise FileNotFoundError(f"not a directory: {p}")
    return sorted(p.glob("*.dcm"))


def extract_phi_fields(ds) -> Dict[str, str]:
    return {t: str(getattr(ds, t)) for t in PHI_TAGS
            if getattr(ds, t, None) not in (None, "")}


def deid_report(path) -> List[Dict[str, str]]:
    import pydicom
    return [{"file": f.name,
             **extract_phi_fields(
                 pydicom.dcmread(str(f), stop_before_pixels=True))}
            for f in scan_dicom_dir(path)]


def ingest_real_series(path, metadata_keys=None, allow_phi=False):
    """Read a real DICOM series through the validated pipeline.

    Refuses (PrivacyGateError) if any identity-bearing string field trips
    phi_scrubber.is_clean == False, unless allow_phi=True (documented
    exception for already-verified on-prem de-identified exports).
    """
    reader = DicomReader(metadata_keys=metadata_keys or SWEEP_TAGS)
    slices = scan_dicom_dir(path)
    if not slices:
        raise FileNotFoundError(f"no .dcm in {path}")
    violations = []
    for f in slices:
        meta = reader.read_metadata(f)
        for key, val in meta.items():
            if isinstance(val, str) and not phi_scrubber.is_clean(val):
                violations.append((f.name, key, val))
    if violations and not allow_phi:
        raise PrivacyGateError(
            f"identifiable data refused ({len(violations)} PHI hits): "
            f"{violations[:5]}")
    records = []
    for f in slices:
        out = reader.read(f)
        rec = dict(out["metadata"])
        rec["min_hu"] = out["min"]
        rec["max_hu"] = out["max"]
        records.append(rec)
    return records
