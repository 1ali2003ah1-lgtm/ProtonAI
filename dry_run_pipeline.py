"""
ProtonAI - Data: Dry-run Pipeline (بيانات اصطناعية 100%)
عرض حي متكامل بدون أي بيانات حقيقية:
CT محاكى فيه PHI وهمي ← parse ← deidentify (PS3.15) ← harmonize ← تقرير.
يرجع {"report", "phi_leak"} — وphi_leak لازم تكون False دائماً.
"""

import json
import logging

import numpy as np

logger = logging.getLogger("ProtonAI.Data.DryRun")

try:
    from pydicom.dataset import Dataset
    from pydicom.sequence import Sequence
    PYDICOM_AVAILABLE = True
except Exception:  # pragma: no cover
    Dataset = None
    Sequence = None
    PYDICOM_AVAILABLE = False

from dicom_parser import parse_ct, parse_rtstruct
from gov_anonymizer import deidentify, is_deidentified
from harmonization import harmonize


def _synthetic_ct():
    if not PYDICOM_AVAILABLE:
        raise RuntimeError("pydicom مطلوب للـ dry-run")
    ds = Dataset()
    ds.Modality = "CT"
    ds.Rows = 64
    ds.Columns = 64
    ds.PixelSpacing = [1.0, 1.0]
    ds.SliceThickness = 2.5
    # PHI وهمي اصطناعي (للاختبار فقط)
    ds.PatientName = "SYNTH PATIENT"
    ds.PatientID = "MRN-000"
    ds.PatientBirthDate = "19800101"
    ds.InstitutionName = "SYNTH HOSPITAL"
    return ds


def _synthetic_rtstruct():
    ds = Dataset()
    gtv = Dataset(); gtv.ROINumber = 1; gtv.ROIName = "GTV"
    oar = Dataset(); oar.ROINumber = 2; oar.ROIName = "BRAINSTEM"
    ds.StructureSetROISequence = Sequence([gtv, oar])
    return ds


def run_dry_run(site: str = "CT-SIM-01",
                pseudonym: str = "P-DRY-001", seed: int = 0) -> dict:
    """تشغيل الخط الكامل على بيانات اصطناعية والتحقق من صفر PHI"""
    ct = _synthetic_ct()
    phi = [str(ct.PatientName), str(ct.PatientID),
           str(ct.PatientBirthDate), str(ct.InstitutionName)]

    geo = parse_ct(ct)
    deidentify(ct, pseudonym)
    deid = is_deidentified(ct)

    rois = [r["name"] for r in parse_rtstruct(_synthetic_rtstruct())]
    img = np.random.default_rng(seed).uniform(-1000, 1000, (8, 8))
    harm = harmonize(img, (1.0, 1.0), site)

    report = {
        "site": site,
        "pseudonym": pseudonym,
        "geometry": geo,
        "rois": rois,
        "deidentified": deid,
        "image_range": [float(harm["image"].min()), float(harm["image"].max())],
    }
    blob = json.dumps(report, ensure_ascii=False)
    leak = any(p and p in blob for p in phi)
    logger.info(f"dry-run {site}: phi_leak={leak}")
    return {"report": report, "phi_leak": leak}
