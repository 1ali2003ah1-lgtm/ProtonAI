"""
ProtonAI - Organ-at-Risk (OAR) Segmenter
تقسيم الأعضاء المعرضة للخطر: نطاق HU + قناع مكاني (region) اختياري
قيم HU وحدها لا تفرّق الأعضاء المتشابهة، فالـ region هو الطريقة الكلاسيكية للتمييز
(بنفس API الطبقة B للاتساق؛ الطبقة العصبة لاحقاً تملأ الـ regions تلقائياً)
"""

import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger("ProtonAI.OARSegmenter")

# نطاقات HU تقريبية لأعضاء شائعة (التمييز الفعلي بينها يحتاج region_masks)
DEFAULT_OAR_RANGES: Dict[str, Tuple[float, float]] = {
    "lung": (-900.0, -500.0),     # رئة (تُفصل يسار/يمين بالـ region)
    "heart": (30.0, 80.0),        # قلب
    "spinal_cord": (10.0, 30.0),  # نخاع شوكي
    "bone_marrow": (150.0, 400.0),# نخاع عظمي
}

BACKGROUND = "background"


class OARSegmenter:
    """
    مقسّم الأعضاء المعرضة للخطر.
    - segment: قناع bool لكل عضو (HU ∩ region إن وُجد) + background اختياري.
    - organ_map: مصفوفة int (0=لا شيء، i+1=organ_names[i] أبجدياً).
    - volume_fraction / summary: نسبة وملخص لكل عضو.
    """

    def __init__(
        self,
        ranges: Optional[Dict[str, Tuple[float, float]]] = None,
        region_masks: Optional[Dict[str, Any]] = None,
        include_background: bool = False,
    ):
        # تمييز: None = افتراضي، قاموس فارغ صريح = خطأ
        if ranges is None:
            src = dict(DEFAULT_OAR_RANGES)
        else:
            src = dict(ranges)
        if not src:
            raise ValueError("ranges لا يمكن أن تكون فارغة")
        for name, (lo, hi) in src.items():
            if lo >= hi:
                raise ValueError(f"نطاق غير صالح لـ {name}: [{lo}, {hi})")
        self.ranges = {str(k): (float(lo), float(hi)) for k, (lo, hi) in src.items()}
        self.region_masks = dict(region_masks) if region_masks else {}
        self.include_background = include_background
        self.organ_names: List[str] = sorted(self.ranges.keys())

    def _check_pixels(self, pixels: Any) -> np.ndarray:
        """التحقق والتحويل لمصفوفة numpy"""
        arr = np.asarray(pixels)
        if arr.size == 0:
            raise ValueError("pixels فارغة")
        return arr.astype(float)

    def _organ_mask(self, arr: np.ndarray, name: str) -> np.ndarray:
        """قناع عضو واحد: HU ∩ region (مع التحقق من حجم الـ region)"""
        lo, hi = self.ranges[name]
        m = (arr >= lo) & (arr < hi)
        if name in self.region_masks:
            rm = np.asarray(self.region_masks[name], dtype=bool)
            if rm.shape != arr.shape:
                raise ValueError(
                    f"region_mask لـ {name} بحجم {rm.shape} ≠ pixels {arr.shape}")
            m = m & rm
        return m

    def _background_mask(self, arr: np.ndarray) -> np.ndarray:
        """قناع الخلفية: كل بكسل لا ينتمي لأي عضو"""
        classified = np.zeros(arr.shape, dtype=bool)
        for name in self.organ_names:
            classified |= self._organ_mask(arr, name)
        return ~classified

    def segment(self, pixels: Any) -> Dict[str, np.ndarray]:
        """أقنعة كل الأعضاء (+ background إن مُفعّل)"""
        arr = self._check_pixels(pixels)
        masks = {name: self._organ_mask(arr, name) for name in self.organ_names}
        if self.include_background:
            masks[BACKGROUND] = self._background_mask(arr)
        return masks

    def organ_map(self, pixels: Any) -> np.ndarray:
        """خريطة أعضاء: 0 = لا شيء، i+1 = organ_names[i] (أبجدياً)"""
        arr = self._check_pixels(pixels)
        masks = self.segment(arr)  # يعيد استخدام التحقق من الـ region
        out = np.zeros(arr.shape, dtype=int)
        for i, name in enumerate(self.organ_names, start=1):
            out[masks[name]] = i
        return out

    def volume_fraction(self, pixels: Any, organ: str) -> float:
        """نسبة بكسلات عضو معيّن (0..1)"""
        arr = self._check_pixels(pixels)
        if organ == BACKGROUND:
            mask = self._background_mask(arr)
        else:
            if organ not in self.ranges:
                raise ValueError(f"عضو غير معروف: {organ}")
            mask = self._organ_mask(arr, organ)
        return float(mask.sum()) / float(arr.size)

    def summary(self, pixels: Any) -> Dict[str, Dict[str, Any]]:
        """ملخص لكل عضو: count + fraction + mean_hu"""
        arr = self._check_pixels(pixels)
        masks = self.segment(arr)
        total = float(arr.size)
        keys = self.organ_names + ([BACKGROUND] if self.include_background else [])
        out: Dict[str, Dict[str, Any]] = {}
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
