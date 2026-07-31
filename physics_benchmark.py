"""
ProtonAI - Physics Benchmark
مقارنة المحرك الفيزيائي بحسابات/قيم مرجعية معروفة (PSTAR/ICRU للمدى بالماء)
+ التحقق من الخصائص الفيزيائية الثابتة (RSP الماء=1، monotonic، RBE)
يقيس الخطأ النسبي بصراحة (نموذج CSDA تقريبي ~1-2%) بدل إخفائه
"""

import logging
from typing import Any, Dict, List, Optional

from proton_physics import ProtonPhysics

logger = logging.getLogger("ProtonAI.PhysicsBenchmark")

# قيم مرجعية للمدى بالماء (mm) من جداول PSTAR/ICRU التقريبية
# (تُستخدم كمعيار مقارنة؛ النموذج CSDA يقاربها ضمن ~2%)
DEFAULT_RANGE_BENCHMARK: Dict[float, float] = {
    70.0: 40.3,
    100.0: 77.4,
    150.0: 157.7,
    200.0: 258.0,
    250.0: 379.0,
}

DEFAULT_RANGE_TOLERANCE = 0.05  # 5% — تسامح مقبول لنموذج CSDA مبسط


class PhysicsBenchmark:
    """
    مقارن المعايير الفيزيائية.
    - range_relative_error: الخطأ النسبي للمدى عند طاقة معيّنة مقابل المرجع.
    - range_errors: أخطاء قائمة طاقات.
    - within_range_tolerance: هل كل الأخطاء ضمن التسامح؟
    - rsp_water_is_one / rbe_consistent / range_monotonic: خصائص ثابتة.
    - summary: تقرير شامل + all_passed.
    """

    def __init__(
        self,
        physics: Optional[ProtonPhysics] = None,
        range_reference: Optional[Dict[float, float]] = None,
        range_tolerance: float = DEFAULT_RANGE_TOLERANCE,
    ):
        if range_tolerance < 0:
            raise ValueError("range_tolerance يجب أن يكون >= 0")
        self.physics = physics if physics is not None else ProtonPhysics()
        self.range_reference = (dict(range_reference) if range_reference
                                else dict(DEFAULT_RANGE_BENCHMARK))
        self.range_tolerance = range_tolerance

    def range_relative_error(self, energy_mev: float) -> float:
        """الخطأ النسبي |calc - ref| / ref لطاقة معيّنة (KeyError لو مو بالمرجع)"""
        if energy_mev not in self.range_reference:
            raise KeyError(f"طاقة غير موجودة بالمرجع: {energy_mev}")
        ref = self.range_reference[energy_mev]
        if ref <= 0:
            raise ValueError(f"القيمة المرجعية للطاقة {energy_mev} يجب أن تكون > 0")
        calc = self.physics.water_range_mm(energy_mev)
        return abs(calc - ref) / ref

    def range_errors(
        self, energies: Optional[List[float]] = None
    ) -> Dict[float, float]:
        """الخطأ النسبي لكل طاقة (الافتراضي = كل طاقات المرجع)"""
        keys = list(energies) if energies is not None else list(self.range_reference.keys())
        return {e: self.range_relative_error(e) for e in keys}

    def within_range_tolerance(
        self,
        tolerance: Optional[float] = None,
        energies: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        """هل كل أخطاء المدى ضمن التسامح؟ (passed=True لو لا طاقات = vacuously)"""
        t = self.range_tolerance if tolerance is None else float(tolerance)
        if t < 0:
            raise ValueError("tolerance يجب أن يكون >= 0")
        errs = self.range_errors(energies)
        passed = all(e <= t for e in errs.values()) if errs else True
        logger.info(f"range benchmark: passed={passed}, tol={t}, "
                    f"max_err={max(errs.values()) if errs else 0.0:.4f}")
        return {"passed": passed, "tolerance": t, "errors": errs}

    def rsp_water_is_one(self, tol: float = 1e-9) -> bool:
        """RSP للماء (HU=0) يجب أن يكون 1.0 بالضبط (تعريف)"""
        return abs(self.physics.rsp_from_hu(0.0) - 1.0) <= tol

    def rbe_consistent(self, tol: float = 1e-9) -> bool:
        """rbe_dose(1) يجب أن يساوي default_rbe (تعريف سريري)"""
        return abs(self.physics.rbe_dose(1.0) - self.physics.default_rbe) <= tol

    def range_monotonic(self, energies: Optional[List[float]] = None) -> bool:
        """المدى يتزايد صارماً مع الطاقة (خاصية فيزيائية أساسية)"""
        keys = sorted(energies) if energies is not None else sorted(self.range_reference.keys())
        if len(keys) < 2:
            return True
        ranges = [self.physics.water_range_mm(e) for e in keys]
        return all(ranges[i] < ranges[i + 1] for i in range(len(ranges) - 1))

    def summary(self) -> Dict[str, Any]:
        """تقرير شامل + all_passed"""
        check = self.within_range_tolerance()
        errs = check["errors"]
        rsp_ok = self.rsp_water_is_one()
        rbe_ok = self.rbe_consistent()
        mono_ok = self.range_monotonic()
        return {
            "range_within_tolerance": check["passed"],
            "range_tolerance": check["tolerance"],
            "range_errors": errs,
            "max_range_error": max(errs.values()) if errs else 0.0,
            "rsp_water_is_one": rsp_ok,
            "rbe_consistent": rbe_ok,
            "range_monotonic": mono_ok,
            "all_passed": bool(check["passed"] and rsp_ok and rbe_ok and mono_ok),
}
