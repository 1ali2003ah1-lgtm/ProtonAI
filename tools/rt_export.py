from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np
import pydicom
from pydicom.dataset import Dataset, FileDataset
from pydicom.sequence import Sequence
from pydicom.uid import ExplicitVRLittleEndian, generate_uid
from scipy.ndimage import binary_dilation, binary_erosion

RTSTRUCT_UID = "1.2.840.10008.5.1.4.1.1.481.3"


def _boundary_points(mask, spacing=(1.0, 1.0), origin=(0.0, 0.0), z=0.0):
    m = np.asarray(mask) > 0.5
    if not m.any():
        return [float(origin[0]), float(origin[1]), float(z)]
    edges = m & ~binary_erosion(m)
    ys, xs = np.nonzero(edges)
    if len(xs) > 2:
        cx, cy = xs.mean(), ys.mean()
        o = np.argsort(np.arctan2(ys - cy, xs - cx))
        xs, ys = xs[o], ys[o]
    pts = []
    for y, x in zip(ys, xs):
        pts += [float(origin[0] + x * spacing[0]),
                float(origin[1] + y * spacing[1]), float(z)]
    return pts


def _make_roi(num, name, color, mask3d, spacing, origin, th):
    roi = Dataset(); roi.ROINumber = num; roi.ROIName = name
    roi.ReferencedFrameOfReferenceUID = generate_uid()
    roi.ROIGenerationAlgorithm = "AUTOMATIC"
    conts = []
    for z in range(mask3d.shape[0]):
        if mask3d[z].sum() == 0:
            continue
        pts = _boundary_points(mask3d[z], (spacing[1], spacing[2]), origin,
                               origin[2] + z * th)
        c = Dataset(); c.ContourGeometricType = "CLOSED_PLANAR"
        c.NumberOfContourPoints = len(pts) // 3; c.ContourData = pts
        conts.append(c)
    rc = Dataset(); rc.ReferencedROINumber = num; rc.ROIDisplayColor = color
    rc.ContourSequence = Sequence(conts)
    return roi, rc


def export_rtstruct(gtv, path, oar_masks=None, spacing=(1.0, 1.0, 1.0),
                    origin=(0.0, 0.0, 0.0), generate_ctv=True,
                    ctv_margin_mm=5.0):
    gtv = np.asarray(gtv)
    if gtv.ndim == 2:
        gtv = gtv[None, :, :]
    fm = Dataset(); fm.MediaStorageSOPClassUID = RTSTRUCT_UID
    fm.MediaStorageSOPInstanceUID = generate_uid()
    fm.TransferSyntaxUID = ExplicitVRLittleEndian
    ds = FileDataset(str(path), {}, file_meta=fm, preamble=b"\x00" * 128)
    ds.SOPClassUID = RTSTRUCT_UID; ds.SOPInstanceUID = fm.MediaStorageSOPInstanceUID
    ds.Modality = "RTSTRUCT"; ds.StructureSetLabel = "ProtonAI"
    ds.StructureSetName = "ProtonAI-Auto"; ds.SeriesInstanceUID = generate_uid()
    rois, rcs = [], []
    r, c = _make_roi(1, "GTV", [255, 0, 0], gtv, spacing, origin, spacing[0])
    rois.append(r); rcs.append(c)
    if generate_ctv:
        ctv = binary_dilation(gtv, iterations=int(ctv_margin_mm / spacing[1]))
        r, c = _make_roi(2, "CTV", [255, 255, 0], ctv.astype(np.uint8),
                         spacing, origin, spacing[0])
        rois.append(r); rcs.append(c)
    colors = {"SpinalCord": [0, 0, 255], "Brainstem": [0, 255, 255],
              "Parotid_L": [255, 128, 0], "Parotid_R": [0, 255, 0],
              "Heart": [255, 0, 255], "Lung_L": [128, 128, 255],
              "Lung_R": [255, 128, 128]}
    for i, (nm, mk) in enumerate((oar_masks or {}).items(), start=3):
        mk = np.asarray(mk)
        if mk.ndim == 2:
            mk = mk[None, :, :]
        r, c = _make_roi(i, nm, colors.get(nm, [128, 128, 128]), mk,
                         spacing, origin, spacing[0])
        rois.append(r); rcs.append(c)
    ds.StructureSetROISequence = Sequence(rois)
    ds.ROIContourSequence = Sequence(rcs)
    ds.save_as(str(path))
    return Path(path)
