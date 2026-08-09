"""
ProtonAI - AI: Segmentation Metrics
مقاييس تقسيم احترافية من أقنعة ثنائية (numpy):
- Dice: تداخل.
- HD95: مسافة Hausdorff بالمئة 95 (أقل حساسية للقيم الشاذة).
- ASSD: متوسط المسافة السطحية المتماثل.
"""

import numpy as np


def _coords(mask):
    return np.argwhere(np.asarray(mask, dtype=bool))


def dice(a, b) -> float:
    """معامل Dice؛ 1.0 إذا كان القناعان فارغين"""
    a = np.asarray(a, dtype=bool)
    b = np.asarray(b, dtype=bool)
    sa, sb = a.sum(), b.sum()
    if sa == 0 and sb == 0:
        return 1.0
    if sa == 0 or sb == 0:
        return 0.0
    inter = (a & b).sum()
    return float(2 * inter / (sa + sb))


def _pairwise(A, B):
    return np.sqrt(((A[:, None, :] - B[None, :, :]) ** 2).sum(-1))


def hd95(a, b) -> float:
    """مسافة Hausdorff بالمئة 95؛ inf إذا كان أحد القناعين فارغاً"""
    A, B = _coords(a), _coords(b)
    if len(A) == 0 or len(B) == 0:
        return float("inf")
    D = _pairwise(A, B)
    return float(max(np.percentile(D.min(axis=1), 95),
                     np.percentile(D.min(axis=0), 95)))


def assd(a, b) -> float:
    """متوسط المسافة السطحية المتماثل؛ inf إذا كان أحد القناعين فارغاً"""
    A, B = _coords(a), _coords(b)
    if len(A) == 0 or len(B) == 0:
        return float("inf")
    D = _pairwise(A, B)
    return float((D.min(axis=1).mean() + D.min(axis=0).mean()) / 2)


def report(pred, gt) -> dict:
    """تقرير مقاييس كامل لتقييم نموذج تقسيم"""
    return {"dice": dice(pred, gt), "hd95": hd95(pred, gt),
            "assd": assd(pred, gt)}
