"""
ProtonAI - DICOM Reader
بوابة قراءة ملفات DICOM: استخراج metadata + pixels بقيم HU بشكل آمن
استيراد pydicom كسول (lazy) لحماية المنصة لو المكتبة غير مثبتة
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger("ProtonAI.DicomReader")

# حقول metadata الشائعة (نستخرجها كسلاسل آمنة)
DEFAULT_METADATA_KEYS: List[str] = [
    "PatientID", "PatientName", "PatientBirthDate", "PatientSex",
    "StudyDate", "Modality", "Manufacturer",
    "Rows", "Columns", "BitsAllocated",
    "PixelSpacing", "SliceThickness",
    "RescaleSlope", "RescaleIntercept",
    "WindowCenter", "WindowWidth",
]


def _load_pydicom():
    """استيراد pydicom كسولاً مع رسالة خطأ لطيفة إن لم يُثبّت"""
    try:
        import pydicom
        return pydicom
    except ImportError as e:
        raise ImportError(
            "مكتبة pydicom غير مثبتة. ثبّتها عبر: pip install pydicom"
        ) from e


class DicomReader:
    """
    قارئ DICOM.
    - read_metadata: الحقول المطلوبة كقاموس (بدون تحميل pixels).
    - read_pixels: مصفوفة البكسلات (numpy float) مع تطبيق Rescale (→ HU).
    - read: metadata + pixels + إحصاءات معاً.
    - is_dicom: فحص سريع هل الملف DICOM صالح.
    """

    def __init__(self, metadata_keys: Optional[List[str]] = None):
        self.metadata_keys = (list(metadata_keys) if metadata_keys
                              else list(DEFAULT_METADATA_KEYS))

    def _load_dataset(self, path):
        """تحميل dataset مع lazy import"""
        pydicom = _load_pydicom()
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"ملف DICOM غير موجود: {p}")
        return pydicom.dcmread(str(p))

    def is_dicom(self, path) -> bool:
        """فحص سريع: هل الملف DICOM قابل للقراءة"""
        try:
            self._load_dataset(path)
            return True
        except Exception:
            return False

    def read_metadata(self, path) -> Dict[str, Any]:
        """استخراج metadata المطلوبة فقط (حقول غائبة = None)"""
        ds = self._load_dataset(path)
        out: Dict[str, Any] = {}
        for key in self.metadata_keys:
            if hasattr(ds, key):
                val = getattr(ds, key)
                out[key] = str(val) if val is not None else None
            else:
                out[key] = None
        out["_path"] = str(Path(path))
        return out

    def read_pixels(self, path, apply_rescale: bool = True):
        """تحميل مصفوفة البكسلات (float) مع تحويل HU اختياري"""
        ds = self._load_dataset(path)
        pixels = ds.pixel_array.astype(float)
        if apply_rescale:
            slope = float(getattr(ds, "RescaleSlope", 1.0) or 1.0)
            intercept = float(getattr(ds, "RescaleIntercept", 0.0) or 0.0)
            pixels = pixels * slope + intercept
        return pixels

    def read(self, path, apply_rescale: bool = True) -> Dict[str, Any]:
        """metadata + pixels + إحصاءات معاً"""
        meta = self.read_metadata(path)
        pixels = self.read_pixels(path, apply_rescale=apply_rescale)
        return {
            "metadata": meta,
            "pixels": pixels,
            "shape": list(pixels.shape),
            "min": float(pixels.min()),
            "max": float(pixels.max()),
}
