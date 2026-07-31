"""
ProtonAI - Proton Physics Engine
المحرك الفيزيائي الأساسي: مدى البروتون + Bragg Peak + SOBP + RSP من HU + RBE
نماذج تحليلية/هندسية مبسطة (CSDA تقريبي) — مو Monte Carlo.
موثّقة وقابلة للاستبدال بمحاكاة حقيقية لاحقاً عبر نفس الواجهة.
الجسر مع التصوير: المدى بمادة يُحسب من قيم HU (dicom_reader).
"""

import math
import logging
import numpy as np
from typing import Any, Optional

logger = logging.getLogger("ProtonAI.ProtonPhysics")


class ProtonPhysics:
    """
    محرك فيزياء البروتون.
    - water_range_mm / energy_from_range_mm: مدى CSDA تقريبي بالماء وعكسه.
    - rsp_from_hu: relative stopping power من HU (نموذج قطعتين).
    - proton_range_in_medium: المدى الفيزيائي بمادة من ملف HU (تكامل WEPL).
    - bragg_peak / sobp: منحنيات الجرعة.
    - rbe_dose: الجرعة المرجّحة بيولوجياً.
    """

    def __init__(
        self,
        range_a: float = 0.022,      # ثابت CSDA تقريبي (mm)
        range_p: float = 1.77,       # أس الطاقة (CSDA تقريبي للبروتون)
        slope_neg: float = 0.0010,   # ميل RSP للـ HU السالب
        slope_pos: float = 0.0008,   # ميل RSP للـ HU الموجب
        rsp_floor: float = 0.01,     # حد أدنى لـ RSP (حماية التكامل)
        default_rbe: float = 1.1,    # RBE السريري الافتراضي للبروتون
    ):
        if range_a <= 0:
            raise ValueError("range_a يجب أن يكون > 0")
        if range_p <= 0:
            raise ValueError("range_p يجب أن يكون > 0")
        if rsp_floor <= 0:
            raise ValueError("rsp_floor يجب أن يكون > 0")
        if default_rbe <= 0:
            raise ValueError("default_rbe يجب أن يكون > 0")
        self.range_a = range_a
        self.range_p = range_p
        self.slope_neg = slope_neg
        self.slope_pos = slope_pos
        self.rsp_floor = rsp_floor
        self.default_rbe = default_rbe

    def water_range_mm(self, energy_mev: float) -> float:
        """المدى بالماء (mm) من الطاقة (MeV) — CSDA تقريبي: R = a·E^p"""
        if energy_mev <= 0:
            raise ValueError("energy_mev يجب أن يكون > 0")
        return self.range_a * (energy_mev ** self.range_p)

    def energy_from_range_mm(self, range_mm: float) -> float:
        """الطاقة (MeV) من المدى بالماء (mm) — عكس water_range"""
        if range_mm <= 0:
            raise ValueError("range_mm يجب أن يكون > 0")
        return (range_mm / self.range_a) ** (1.0 / self.range_p)

    def rsp_from_hu(self, hu: float) -> float:
        """relative stopping power من HU (نموذج قطعتين + حد أدنى)"""
        hu = float(hu)
        rsp = (1.0 + self.slope_neg * hu) if hu < 0 else (1.0 + self.slope_pos * hu)
        return max(rsp, self.rsp_floor)

    def proton_range_in_medium(
        self, energy_mev: float, hu_profile_1d: Any, voxel_mm: float = 1.0
    ) -> float:
        """
        المدى الفيزيائي (mm) بمادة من ملف HU أحادي البعد.
        يمشي voxel voxel يراكم WEPL = Σ(rsp·voxel_mm) حتى يستنفذ المدى المائي.
        (الجسر مع التصوير: hu_profile يأتي من dicom_reader/tissue_segmenter)
        """
        arr = np.asarray(hu_profile_1d, dtype=float)
        if arr.size == 0:
            raise ValueError("hu_profile_1d فارغ")
        if voxel_mm <= 0:
            raise ValueError("voxel_mm يجب أن يكون > 0")
        water_r = self.water_range_mm(energy_mev)
        wepl = 0.0
        for i, h in enumerate(arr):
            step = self.rsp_from_hu(h) * voxel_mm
            if wepl + step >= water_r:
                remain = water_r - wepl
                frac = (remain / step) if step > 0 else 0.0
                return (i + frac) * voxel_mm
            wepl += step
        # البروتون لم يتوقف داخل المصفوفة → يرجع طولها الكامل
        return float(arr.size * voxel_mm)

    def bragg_peak(
        self, depths_mm: Any, range_mm: float,
        peak_height: float = 1.0, sigma_mm: float = 2.0, plateau_slope: float = 0.3,
    ) -> np.ndarray:
        """
        منحنى Bragg Peak شبه-تجريبي: ذيل دخول صاعد + ذروة حادة عند المدى + سقوط.
        (نموذج شكلي موثّق، لا يحاكي تشتت الطاقة بدقة Monte Carlo)
        """
        z = np.asarray(depths_mm, dtype=float)
        if range_mm <= 0:
            raise ValueError("range_mm يجب أن يكون > 0")
        if sigma_mm <= 0:
            raise ValueError("sigma_mm يجب أن يكون > 0")
        plateau = np.where(z <= range_mm,
                           plateau_slope * np.clip(z / range_mm, 0.0, 1.0), 0.0)
        peak = peak_height * np.exp(-0.5 * ((z - range_mm) / sigma_mm) ** 2)
        return plateau + peak

    def sobp(
        self, depths_mm: Any, target_start_mm: float, target_end_mm: float,
        n_peaks: int = 5, sigma_mm: float = 2.0, peak_height: float = 1.0,
        weights: Optional[Any] = None,
    ) -> np.ndarray:
        """
        Spread-Out Bragg Peak: تراكب n_peaks منحنيات Bragg لتغطية منطقة الهدف.
        (أوزان متساوية افتراضياً = مبسطة؛ التسطيح الأمثل = تحسين مستقبلي)
        """
        if n_peaks < 1:
            raise ValueError("n_peaks يجب أن يكون >= 1")
        if target_end_mm <= target_start_mm:
            raise ValueError("target_end_mm يجب أن يكون > target_start_mm")
        ranges = np.linspace(target_start_mm, target_end_mm, n_peaks)
        w = np.ones(n_peaks) if weights is None else np.asarray(weights, dtype=float)
        if len(w) != n_peaks:
            raise ValueError("طول weights يجب أن يساوي n_peaks")
        z = np.asarray(depths_mm, dtype=float)
        curve = np.zeros_like(z)
        for wi, r in zip(w, ranges):
            curve = curve + wi * self.bragg_peak(z, float(r), peak_height, sigma_mm)
        return curve

    def rbe_dose(self, physical_dose: Any, rbe: Optional[float] = None) -> Any:
        """الجرعة المرجّحة بيولوجياً = الجرعة الفيزيائية × RBE"""
        r = self.default_rbe if rbe is None else float(rbe)
        if r <= 0:
            raise ValueError("rbe يجب أن يكون > 0")
        arr = np.asarray(physical_dose, dtype=float) * r
        return float(arr) if arr.ndim == 0 else arr
