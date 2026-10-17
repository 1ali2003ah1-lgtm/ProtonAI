from __future__ import annotations
from pathlib import Path
import numpy as np
try:
    import pydicom
    HAS_PYDICOM = True
except ImportError:
    HAS_PYDICOM = False


def find_dicom_series(directory):
    if not HAS_PYDICOM:
        raise ImportError("pydicom required")
    directory = Path(directory)
    out = []
    for p in directory.iterdir():
        if p.is_file() and p.suffix.lower() in ("", ".dcm", ".dicom"):
            try:
                ds = pydicom.dcmread(str(p), stop_before_pixels=True)
                if getattr(ds, "Modality", None) == "CT":
                    pos = getattr(ds, "ImagePositionPatient", None)
                    z = float(pos[2]) if pos else float(getattr(ds, "InstanceNumber", 0))
                    out.append((z, p))
            except Exception:
                continue
    if not out:
        raise ValueError("No CT DICOM files in " + str(directory))
    out.sort(key=lambda x: x[0])
    return [p for _, p in out]


def read_dicom_series(directory):
    paths = find_dicom_series(directory)
    slices, meta, spacing = [], {}, (1.0, 1.0, 1.0)
    for i, p in enumerate(paths):
        ds = pydicom.dcmread(str(p))
        hu = ds.pixel_array.astype(np.float32) * float(getattr(ds, "RescaleSlope", 1.0)) + float(getattr(ds, "RescaleIntercept", 0.0))
        if hu.min() < -2000 or hu.max() > 5000:
            raise ValueError("Slice " + str(i) + ": HU out of range")
        slices.append(hu)
        if i == 0:
            spacing = (float(getattr(ds, "SliceThickness", 1.0)),
                       float(ds.PixelSpacing[0]) if hasattr(ds, "PixelSpacing") else 1.0,
                       float(ds.PixelSpacing[1]) if hasattr(ds, "PixelSpacing") else 1.0)
            meta = {"PatientID": str(getattr(ds, "PatientID", "UNKNOWN")),
                    "StudyInstanceUID": str(getattr(ds, "StudyInstanceUID", "")),
                    "SeriesInstanceUID": str(getattr(ds, "SeriesInstanceUID", "")),
                    "Modality": "CT", "SliceThickness": spacing[0],
                    "PixelSpacing": [spacing[1], spacing[2]], "n_slices": len(paths)}
    return np.stack(slices, 0).astype(np.float32), meta
