"""
ProtonAI - Tissue Segmenter
تقسيم الأنسجة الكلاسيكي بقيم Hounsfield (HU)
يفصل كل بكسل إلى نسيج بقاعدة طبية معروفة (بدون شبكة عصبية / GPU)
"""

import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger("ProtonAI.TissueSegmenter")

# النطاقات الافتراضية (HU) بصيغة [lo, hi) — حتمية وبدون تداخل
# أي قيمة خارج كل النطاقات = unclassified
DEFAULT_TISSUE_RANGES: Dict[str, Tuple[float, float]] = {
    "air": (-1024.0, -900.0),     # هواء / خارج الجسم
    "lung": (-900.0, -500.0),     # نسيج الرئة الهوائي
    "fat": (-190.0, -30.0),       # دهون
    "soft_tissue": (-30.0, 150.0),# أنسجة رخوة / عضل / أعضاء
    "bone": (150.0, 3000.0),      # عظم
}

UNCLASSIFIED = "unclassified"


class TissueSegmenter:
    """
    مقسّم الأنسجة.
    - segment: قناع (mask) bool لكل نسيج (+ unclassified اختياري).
    - tissue_map: مصفوفة int (0=unclassified، 1..k بالترتيب الأبجدي).
    - volume_fraction: نسبة بكسلات نسيج معيّن.
    - summary: لكل نسيج {count, fraction, mean_hu}.
    """

    def __init__(
        self,
        ranges: Optional[Dict[str, Tuple[float, float]]] = None,
        include_unclassified: bool = True,
    ):
        src = dict(ranges) if ranges else dict(DEFAULT_TISSUE_RANGES)
        if not src:
            raise ValueError("ranges لا يمكن أن تكون فارغة")
        # التحقق من صحة النطاقات
        for name, (lo, hi) in src.items():
            if lo >= hi:
                raise ValueError(f"نطاق غير صالح لـ {name}: [{lo}, {hi})")
        self.ranges = {str(k): (float(lo), float(hi)) for k, (lo, hi) in src.items()}
        self.include_unclassified = include_unclassified
        # ترتيب ثابت للفئات (أبجدي) → حتمي
        self.tissue_names: List[str] = sorted(self.ranges.keys())

    def _check_pixels(self, pixels: Any) -> np.ndarray:
        """التحقق والتحويل لمصفوفة numpy"""
        arr = np.asarray(pixels)
        if arr.size == 0:
            raise ValueError("pixels فارغة")
        return arr.astype(float)

    def _mask_for(self, pixels: np.ndarray, name: str) -> np.ndarray:
        """قناع نسيج واحد: lo <= v < hi"""
        lo, hi = self.ranges[name]
        return (pixels >= lo) & (pixels < hi)

    def segment(self, pixels: Any) -> Dict[str, np.ndarray]:
        """أقنعة كل الأنسجة (+ unclassified إن مُفعّل)"""
        arr = self._check_pixels(pixels)
        masks = {name: self._mask_for(arr, name) for name in self.tissue_names}
        if self.include_unclassified:
            classified = np.zeros(arr.shape, dtype=bool)
            for m in masks.values():
                classified |= m
            masks[UNCLASSIFIED] = ~classified
        return masks

    def tissue_map(self, pixels: Any) -> np.ndarray:
        """
        خريطة فئات: 0 = unclassified، i+1 = tissue_names[i]
        (الترتيب الأبجدي يضمن الحتمية)
        """
        arr = self._check_pixels(pixels)
        out = np.zeros(arr.shape, dtype=int)
        for i, name in enumerate(self.tissue_names, start=1):
            out[self._mask_for(arr, name)] = i
        return out

    def volume_fraction(self, pixels: Any, tissue: str) -> float:
        """نسبة بكسلات نسيج معيّن (0..1)"""
        arr = self._check_pixels(pixels)
        if tissue == UNCLASSIFIED:
            masks = self.segment(arr)
            mask = masks.get(UNCLASSIFIED)
            if mask is None:
                # بدون unclassified: النسبة = ما تبقّى بعد كل الأنسجة
                classified = np.zeros(arr.shape, dtype=bool)
                for name in self.tissue_names:
                    classified |= self._mask_for(arr, name)
                mask = ~classified
        else:
            if tissue not in self.ranges:
                raise ValueError(f"نسيج غير معروف: {tissue}")
            mask = self._mask_for(arr, tissue)
        return float(mask.sum()) / float(arr.size)

    def summary(self, pixels: Any) -> Dict[str, Dict[str, Any]]:
        """ملخص لكل نسيج: count + fraction + mean_hu"""
        arr = self._check_pixels(pixels)
        masks = self.segment(arr)  # يشمل unclassified إن مُفعّل
        total = float(arr.size)
        out: Dict[str, Dict[str, Any]] = {}
        keys = self.tissue_names + ([UNCLASSIFIED] if self.include_unclassified else [])
        for name in keys:
            mask = masks.get(name)
            if mask is None:
                continue
            count = int(mask.sum())
            vals = arr[mask]
            out[name] = {
                "count": count,
                "fraction": count / total,
                "mean_hu": float(vals.mean()) if count > 0 else None,
            }
        return out
