"""
ProtonAI - Pretrained Segmenter
واجهة نموذج segmentation جاهز (pre-trained) + نموذج demo مبني على قواعد
الواجهة قابلة للحقن (dependency injection): نموذج torch حقيقي يُمرَّر كـ callable
بنفس الواجهة لاحقاً، بدون تعديل. نموذج الـ demo يملأ region masks للطبقة C (OAR).
لا يستورد torch → آمن على CI؛ الشبكة الحقيقية تُركَّب على الجهاز.
"""

import logging
import numpy as np
from typing import Dict, Any, Optional, Callable

from oar_segmenter import OARSegmenter, DEFAULT_OAR_RANGES

logger = logging.getLogger("ProtonAI.PretrainedSegmenter")


class RuleBasedDemoModel:
    """
    نموذج demo حتمي مبني على قواعد (HU ∩ منطقة هندسية بنسبة الأبعاد).
    يحاكي نموذجاً جاهزاً لأغراض الاختبار والعرض، ويملأ region masks للـ OAR.
    يدعم 2D فقط (الـ 3D الحقيقي يأتي مع نموذج torch لاحقاً).
    """

    # مناطق هندسية ثابتة (نسب من الأبعاد) للأعضاء المعروفة بالـ demo
    _DEMO_REGIONS = {
        "heart": (0.25, 0.75, 0.0, 0.5),     # (r0,r1,c0,c1) وسط-يسار
        "spinal_cord": (0.0, 1.0, 0.4, 0.6), # عمود مركزي رفيع
        # lung / bone_marrow: كل الصورة (يُفصلان بالـ HU أساساً)
    }

    def __init__(self, ranges: Optional[Dict[str, tuple]] = None):
        self.ranges = dict(ranges) if ranges else dict(DEFAULT_OAR_RANGES)

    def _check_2d(self, pixels: Any) -> np.ndarray:
        """التحقق: demo يدعم 2D فقط"""
        arr = np.asarray(pixels, dtype=float)
        if arr.ndim != 2:
            raise ValueError(f"نموذج الـ demo يدعم 2D فقط، وصل {arr.ndim}D")
        if arr.size == 0:
            raise ValueError("pixels فارغة")
        return arr

    def region_masks(self, pixels: Any) -> Dict[str, np.ndarray]:
        """المناطق المكانية للأعضاء (بدون HU) — تُحقن بالـ OAR"""
        arr = self._check_2d(pixels)
        H, W = arr.shape
        out: Dict[str, np.ndarray] = {}
        for name in self.ranges:
            if name in self._DEMO_REGIONS:
                r0, r1, c0, c1 = self._DEMO_REGIONS[name]
                m = np.zeros((H, W), dtype=bool)
                m[int(r0 * H):int(r1 * H), int(c0 * W):int(c1 * W)] = True
                out[name] = m
            # الأعضاء غير المعروفة بالـ demo → بلا region (تُفصل بالـ HU فقط)
        return out

    def predict(self, pixels: Any) -> Dict[str, np.ndarray]:
        """أقنعة الأعضاء النهائية: HU ∩ region (متسق مع OARSegmenter تماماً)"""
        arr = self._check_2d(pixels)
        regs = self.region_masks(arr)
        out: Dict[str, np.ndarray] = {}
        for name, (lo, hi) in self.ranges.items():
            m = (arr >= lo) & (arr < hi)
            if name in regs:
                m = m & regs[name]
            out[name] = m
        return out


class PretrainedSegmenter:
    """
    واجهة النموذج الجاهز.
    - model=None → RuleBasedDemoModel (يعمل بدون torch).
    - model=callable → نموذج حقيقي (torch/monai) بنفس واجهة predict/region_masks.
    - predict / region_masks: تمرير مباشر للنموذج.
    - build_oar_segmenter: الجسر → OARSegmenter بالـ regions المحسوبة.
    - is_real_model: هل النموذج محقون (حقيقي) أم demo.
    """

    def __init__(
        self,
        model: Optional[Any] = None,
        ranges: Optional[Dict[str, tuple]] = None,
    ):
        self.ranges = dict(ranges) if ranges else dict(DEFAULT_OAR_RANGES)
        if model is None:
            self.model = RuleBasedDemoModel(self.ranges)
            self._is_real = False
        else:
            self.model = model
            self._is_real = True

    @property
    def is_real_model(self) -> bool:
        """True لو النموذج محقون خارجياً (حقيقي)، False لو demo"""
        return self._is_real

    def predict(self, pixels: Any) -> Dict[str, np.ndarray]:
        """أقنعة الأعضاء النهائية من النموذج"""
        return self.model.predict(pixels)

    def region_masks(self, pixels: Any) -> Dict[str, np.ndarray]:
        """المناطق المكانية (لحقنها بالـ OAR)"""
        return self.model.region_masks(pixels)

    def build_oar_segmenter(self, pixels: Any, **kwargs: Any) -> OARSegmenter:
        """
        الجسر: يبني OARSegmenter بالـ regions المحسوبة من النموذج.
        يضمن أن oar.segment(pixels) == self.predict(pixels) لكل عضو.
        """
        return OARSegmenter(
            ranges=self.ranges,
            region_masks=self.region_masks(pixels),
            **kwargs,
  )
