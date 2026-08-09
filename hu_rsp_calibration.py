"""
ProtonAI - Physics: Stoichiometric HU->RSP Calibration (Schneider)
تحويل وحدات Hounsfield إلى مدى توقف نسبي (RSP) بمنحنى معايرة piecewise-linear.
- منحنى مستقل لكل سكانر (scanner_id) — لأن كل CT له استجابة HU مختلفة.
- عدم يقين RSP موثّق لكل نسيج (يغذي ميزانية عدم يقين المدى لاحقاً).
"""

import numpy as np

# منحنى معايرة افتراضي (نقاط HU, RSP) — يُستبدل بنقاط السكانر الفعلي عند التوفر
DEFAULT_CALIBRATION = [
    (-1000, 0.001),  # هواء
    (-700, 0.15),    # رئة عميقة
    (-300, 0.60),    # رئة/دهون
    (-100, 0.95),    # دهون
    (0, 1.00),       # ماء
    (100, 1.05),     # عضل
    (400, 1.20),     # عظم إسفنجي
    (1000, 1.75),    # عظم كثيف
    (2000, 2.20),    # عظم قشري
]

# عدم يقين RSP لكل نسيج (قيم نسبية) — يُراجع مع الفيزيائي المشرف
TISSUE_RSP_UNC = {
    "air": 0.001, "lung": 0.02, "fat": 0.01, "water": 0.005,
    "muscle": 0.01, "bone": 0.03,
}


class StoichiometricRSP:
    """معايرة stoichiometric HU→RSP لمنحنى سكانر محدد"""

    def __init__(self, points=None, scanner_id: str = "default"):
        pts = sorted(points or DEFAULT_CALIBRATION)
        self.hu = np.array([p[0] for p in pts], dtype=float)
        self.rsp = np.array([p[1] for p in pts], dtype=float)
        self.scanner_id = scanner_id

    def hu_to_rsp(self, hu):
        """تحويل HU (قيمة أو مصفوفة) إلى RSP بالاستيفاء الخطي"""
        return np.interp(np.asarray(hu, dtype=float), self.hu, self.rsp)

    def rsp_uncertainty(self, tissue: str) -> float:
        """عدم يقين RSP لنسيج محدد؛ KeyError لنسيج غير معروف"""
        if tissue not in TISSUE_RSP_UNC:
            raise KeyError(f"نسيج غير معروف: {tissue}")
        return TISSUE_RSP_UNC[tissue]
