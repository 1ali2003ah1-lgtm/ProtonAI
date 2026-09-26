"""Generate a synthetic CT DICOM series for ingestion pipeline testing.

ADR-001: validate the DICOM ingestion path end-to-end on fully controlled
synthetic data before touching any real clinical data.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pydicom
from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.uid import CTImageStorage, ExplicitVRLittleEndian, generate_uid


def build_phantom(size: int = 64, n_slices: int = 8, seed: int = 7):
    rng = np.random.default_rng(seed)
    hu = rng.normal(0.0, 8.0, size=(n_slices, size, size))
    yy, xx = np.mgrid[0:size, 0:size]
    masks = np.zeros((n_slices, size, size), dtype=np.uint8)
    for z in range(n_slices):
        cy = size // 2 + int(rng.integers(-6, 7))
        cx = size // 2 + int(rng.integers(-6, 7))
        r = int(rng.integers(8, 13))
        m = ((yy - cy) ** 2 + (xx - cx) ** 2) <= r ** 2
        masks[z] = m
        hu[z][m] += 300.0
    return hu, masks


def write_series(out_dir: Path, hu, masks, patient_id: str = "SYNTH-001"):
    out_dir.mkdir(parents=True, exist_ok=True)
    gt_dir = out_dir / "ground_truth"
    gt_dir.mkdir(exist_ok=True)
    study_uid, series_uid = generate_uid(), generate_uid()
    for z in range(hu.shape[0]):
        ds = Dataset()
        ds.SOPClassUID = CTImageStorage
        ds.SOPInstanceUID = generate_uid()
        ds.PatientID = patient_id
        ds.PatientName = "SYNTH^PHANTOM"
        ds.StudyDate = "20240101"
        ds.Modality = "CT"
        ds.Manufacturer = "ProtonAI-Synthetic"
        ds.StudyInstanceUID = study_uid
        ds.SeriesInstanceUID = series_uid
        ds.Rows, ds.Columns = hu.shape[1], hu.shape[2]
        ds.BitsAllocated = 16
        ds.BitsStored = 12
        ds.HighBit = 11
        ds.PixelRepresentation = 1
        ds.SamplesPerPixel = 1
        ds.PhotometricInterpretation = "MONOCHROME2"
        ds.RescaleIntercept = -1024.0
        ds.RescaleSlope = 1.0
        ds.PixelSpacing = [1.0, 1.0]
        ds.SliceThickness = 2.5
        ds.InstanceNumber = z + 1
        ds.SliceLocation = float(z) * 2.5
        stored = np.rint(hu[z] - ds.RescaleIntercept).astype(np.int16)
        ds.PixelData = stored.tobytes()
        fm = FileMetaDataset()
        fm.MediaStorageSOPClassUID = CTImageStorage
        fm.MediaStorageSOPInstanceUID = ds.SOPInstanceUID
        fm.TransferSyntaxUID = ExplicitVRLittleEndian
        fm.ImplementationClassUID = generate_uid()
        ds.file_meta = fm
        target = out_dir / f"slice_{z:03d}.dcm"
        try:
            pydicom.dcmwrite(str(target), ds, enforce_file_format=True)
        except TypeError:  # older pydicom
            pydicom.dcmwrite(str(target), ds, write_like_original=False)
    np.save(gt_dir / "hu.npy", hu)
    np.save(gt_dir / "masks.npy", masks)
    return out_dir


def main():
    out = Path("data/synth_ct/SYNTH-001")
    hu, masks = build_phantom()
    write_series(out, hu, masks)
    n = len(list(out.glob("*.dcm")))
    print(f"Wrote {n} slices -> {out}")
    print(f"Ground truth -> {out / 'ground_truth'}")


if __name__ == "__main__":
    main()
