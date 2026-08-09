"""
ProtonAI - AI: Uncertainty-aware Inference
- ensemble/MC-Dropout: متوسط + انتشار (تقدير عدم يقين).
- conformal prediction: عتبة تضمن تغطية ≥ (1-alpha).
- ECE: خطأ المعايرة المتوقع (هل ثقة النموذج تطابق دقته؟).
"""

import numpy as np


def ensemble_mean_std(list_of_probs):
    """متوسط + انحراف معياري عبر أعضاء الـ ensemble أو عينات MC-Dropout"""
    arr = np.stack([np.asarray(p, float) for p in list_of_probs])
    return arr.mean(axis=0), arr.std(axis=0)


def expected_calibration_error(conf, corr, bins: int = 10) -> float:
    """ECE: متوسط |الدقة - الثقة| موزوناً بحجم كل_bin"""
    conf = np.asarray(conf, float)
    corr = np.asarray(corr, float)
    edges = np.linspace(0, 1, bins + 1)
    n = len(conf)
    ece = 0.0
    for i in range(bins):
        m = (conf > edges[i]) & (conf <= edges[i + 1])
        if m.sum() == 0:
            continue
        ece += (m.sum() / n) * abs(corr[m].mean() - conf[m].mean())
    return float(ece)


def conformal_threshold(calib_scores, alpha: float = 0.1) -> float:
    """عتبة conformal: كمّ (1-alpha) لدرجات المعايرة"""
    return float(np.quantile(calib_scores, 1 - alpha))


def conformal_covered(score, threshold) -> bool:
    """هل تقع الدرجة داخل مجموعة الـ conformal؟"""
    return bool(score <= threshold)
