"""
ProtonAI - Data: Multi-center Harmonization
توحيد البيانات بين المراكز المختلفة قبل التدريب:
- target_shape: حساب الأبعاد بعد إعادة أخذ العينات لـ spacing موحّد.
- normalize_hu: قصّ + تحجيم شدة HU لنطاق [0,1].
- harmonize: يجمع التوحيد + إرفاق site metadata لكشف domain shift لاحقاً.
"""

import numpy as np

HU_MIN, HU_MAX = -1000.0, 1000.0


def target_shape(shape, from_spacing, to_spacing) -> tuple:
    """الأبعاد الجديدة بعد إعادة أخذ العينات"""
    return tuple(int(round(s * f / t))
                 for s, f, t in zip(shape, from_spacing, to_spacing))


def normalize_hu(image, hu_min: float = HU_MIN, hu_max: float = HU_MAX):
    """قصّ + تحجيم شدة HU إلى [0,1]"""
    img = np.clip(np.asarray(image, float), hu_min, hu_max)
    return (img - hu_min) / (hu_max - hu_min)


def harmonize(image, spacing, site: str,
              target_spacing=(1.0, 1.0, 1.0)) -> dict:
    """توحيد حالة وإرفاق metadata المركز"""
    return {
        "shape": target_shape(np.asarray(image).shape, spacing, target_spacing),
        "image": normalize_hu(image),
        "site": site,
        "target_spacing": tuple(target_spacing),
  }
