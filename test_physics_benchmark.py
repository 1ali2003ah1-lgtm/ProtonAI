"""
ProtonAI - Test Physics Benchmark
اختبارات المقارنة بالمعايير الفيزيائية (دقة CSDA + خصائص ثابتة)
"""

import pytest
from physics_benchmark import (
    PhysicsBenchmark, DEFAULT_RANGE_BENCHMARK, DEFAULT_RANGE_TOLERANCE,
)
from proton_physics import ProtonPhysics


@pytest.fixture
def bench():
    return PhysicsBenchmark()


class TestRangeError:
    def test_relative_error_formula(self, bench):
        e = 100.0
        calc = bench.physics.water_range_mm(e)
        ref = DEFAULT_RANGE_BENCHMARK[e]
        expected = abs(calc - ref) / ref
        assert bench.range_relative_error(e) == pytest.approx(expected)

    def test_all_errors_positive(self, bench):
        for e in DEFAULT_RANGE_BENCHMARK:
            assert bench.range_relative_error(e) >= 0

    def test_unknown_energy_raises(self, bench):
        with pytest.raises(KeyError):
            bench.range_relative_error(999.0)

    def test_custom_reference_zero_error(self):
        phys = ProtonPhysics()
        exact = phys.water_range_mm(100.0)
        b = PhysicsBenchmark(physics=phys, range_reference={100.0: exact})
        assert b.range_relative_error(100.0) == pytest.approx(0.0)


class TestRangeErrors:
    def test_default_keys(self, bench):
        errs = bench.range_errors()
        assert set(errs.keys()) == set(DEFAULT_RANGE_BENCHMARK.keys())

    def test_subset_energies(self, bench):
        errs = bench.range_errors([100.0, 200.0])
        assert set(errs.keys()) == {100.0, 200.0}

    def test_all_below_three_percent(self, bench):
        # النموذج CSDA يقارب الجداول ضمن ~2% → كل الأخطاء < 3%
        errs = bench.range_errors()
        assert all(e < 0.03 for e in errs.values())


class TestWithinTolerance:
    def test_default_tolerance_passes(self, bench):
        res = bench.within_range_tolerance()
        assert res["passed"] is True
        assert res["tolerance"] == pytest.approx(DEFAULT_RANGE_TOLERANCE)

    def test_strict_tolerance_fails(self, bench):
        res = bench.within_range_tolerance(tolerance=1e-6)
        assert res["passed"] is False

    def test_zero_tolerance_exact_passes(self):
        phys = ProtonPhysics()
        exact = phys.water_range_mm(100.0)
        b = PhysicsBenchmark(physics=phys, range_reference={100.0: exact})
        assert b.within_range_tolerance(tolerance=0.0)["passed"] is True

    def test_errors_included(self, bench):
        res = bench.within_range_tolerance()
        assert set(res["errors"].keys()) == set(DEFAULT_RANGE_BENCHMARK.keys())

    def test_invalid_tolerance_raises(self, bench):
        with pytest.raises(ValueError):
            bench.within_range_tolerance(tolerance=-1)

    def test_empty_energies_vacuously_passes(self, bench):
        assert bench.within_range_tolerance(energies=[])["passed"] is True


class TestFixedProperties:
    def test_rsp_water_is_one(self, bench):
        assert bench.rsp_water_is_one() is True

    def test_rbe_consistent(self, bench):
        assert bench.rbe_consistent() is True

    def test_range_monotonic_default(self, bench):
        assert bench.range_monotonic() is True

    def test_range_monotonic_custom_order(self, bench):
        # تمرير بترتيب عشوائي → يُرتَّب داخلياً ويبقى monotonic
        assert bench.range_monotonic([250.0, 70.0, 150.0]) is True

    def test_monotonic_single_energy_true(self, bench):
        assert bench.range_monotonic([100.0]) is True


class TestSummary:
    def test_keys(self, bench):
        s = bench.summary()
        for k in ["range_within_tolerance", "range_tolerance", "range_errors",
                  "max_range_error", "rsp_water_is_one", "rbe_consistent",
                  "range_monotonic", "all_passed"]:
            assert k in s

    def test_all_passed_true_default(self, bench):
        assert bench.summary()["all_passed"] is True

    def test_all_passed_false_when_tolerance_strict(self):
        b = PhysicsBenchmark(range_tolerance=1e-9)
        assert b.summary()["all_passed"] is False

    def test_max_range_error_consistent(self, bench):
        s = bench.summary()
        assert s["max_range_error"] == pytest.approx(max(s["range_errors"].values()))


class TestInjection:
    def test_uses_injected_physics(self):
        custom = ProtonPhysics(range_a=0.03)
        b = PhysicsBenchmark(physics=custom)
        assert b.physics is custom

    def test_default_builds_physics(self, bench):
        assert isinstance(bench.physics, ProtonPhysics)

    def test_default_reference_loaded(self, bench):
        assert bench.range_reference == DEFAULT_RANGE_BENCHMARK


class TestGuards:
    def test_invalid_tolerance_init(self):
        with pytest.raises(ValueError):
            PhysicsBenchmark(range_tolerance=-0.1)
