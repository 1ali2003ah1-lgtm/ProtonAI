"""
ProtonAI - Statistics: Inter-observer Agreement
أدوات قياس الاتفاق بين قارئين (للتقييم الأعمى):
- cohens_kappa: اتفاق مصحح بالصدفة (فئوي/ثنائي).
- dice_between: اتفاق مكاني بين مقنّعين (يعيد استخدام seg_metrics).
- interpret_kappa: تفسير Landis-Koch.
"""

from seg_metrics import dice


def cohens_kappa(labels_a: list, labels_b: list) -> float:
    """Kappa = (po - pe) / (1 - pe)"""
    if len(labels_a) != len(labels_b) or not labels_a:
        raise ValueError("قوائم غير متطابقة/فارغة")
    n = len(labels_a)
    po = sum(a == b for a, b in zip(labels_a, labels_b)) / n
    cats = sorted(set(labels_a) | set(labels_b))
    pe = sum((labels_a.count(c) / n) * (labels_b.count(c) / n) for c in cats)
    if pe == 1.0:
        return 1.0
    return (po - pe) / (1 - pe)


def interpret_kappa(k: float) -> str:
    """تفسير Landis-Koch"""
    if k < 0.0: return "poor"
    if k < 0.2: return "slight"
    if k < 0.4: return "fair"
    if k < 0.6: return "moderate"
    if k < 0.8: return "substantial"
    return "almost perfect"


def dice_between(mask_a, mask_b) -> float:
    """اتفاق مكاني بين مقنّعي قارئين"""
    return dice(mask_a, mask_b)
