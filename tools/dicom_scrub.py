"""W4 TEAM: DICOM PS3.15 scrubber with retain-options + verification gate."""
from __future__ import annotations

PHI_TAGS = {"PatientName", "PatientID", "PatientBirthDate", "PatientSex",
            "PatientAddress", "InstitutionName", "ReferringPhysicianName",
            "StationName", "OperatorsName", "PatientComments",
            "AccessionNumber", "OtherPatientIDs"}
DEVICE_TAGS = {"InstitutionAddress", "DeviceSerialNumber", "Manufacturer",
               "InstitutionalDepartmentName"}
DATE_TAGS = {"StudyDate", "SeriesDate", "AcquisitionDate", "ContentDate"}


def scrub(meta, retain_dates=False, retain_device=False, extra_phi=()):
    phi = PHI_TAGS | set(extra_phi)
    out = {k: v for k, v in meta.items()
           if k not in phi and (retain_device or k not in DEVICE_TAGS)}
    if retain_dates:
        for d in DATE_TAGS:
            if d in out:
                out[d] = str(out[d])[:4] + "0101"
    else:
        out = {k: v for k, v in out.items() if k not in DATE_TAGS}
    out["PatientIdentityRemoved"] = "YES"
    out["DeidentificationMethod"] = "ProtonAI DICOM PS3.15 basic profile"
    return out


def verify_scrubbed(meta):
    return not (PHI_TAGS & set(meta)) and \
        meta.get("PatientIdentityRemoved") == "YES"
