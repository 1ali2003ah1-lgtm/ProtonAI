"""
ProtonAI - Test Documentation Check
اختبارات فحص التوثيق الداخلي
"""

import types
import sys
from docs_check import (
    _doc_present,
    _missing_classes,
    _missing_functions,
    audit_module,
    audit_all,
    HARDENED_MODULES,
)


class _Documented:
    """كلاس موثّق للتجربة"""
    pass


class _Undocumented:
    pass


def _documented_func():
    """دالة موثّقة للتجربة"""
    return 1


def _undocumented_func():
    return 1


class TestDocPresent:
    def test_class_with_doc(self):
        assert _doc_present(_Documented) is True

    def test_class_without_doc(self):
        assert _doc_present(_Undocumented) is False

    def test_function_with_doc(self):
        assert _doc_present(_documented_func) is True

    def test_function_without_doc(self):
        assert _doc_present(_undocumented_func) is False

    def test_module_doc_present(self):
        import docs_check
        assert _doc_present(docs_check) is True


class TestMissingDetection:
    def _fake_module(self):
        fake = types.ModuleType("fake_docs_xyz")

        class A:
            """موثّق"""

        class B:
            pass

        A.__module__ = "fake_docs_xyz"
        B.__module__ = "fake_docs_xyz"
        fake.A = A
        fake.B = B

        def fa():
            """موثّقة"""

        def fb():
            pass

        fa.__module__ = "fake_docs_xyz"
        fb.__module__ = "fake_docs_xyz"
        fake.fa = fa
        fake.fb = fb

        from pathlib import Path
        fake.Path = Path  # مستورد → يجب تجاهله
        fake.__doc__ = """وحدة وهمية"""
        return fake

    def test_missing_classes_finds_undocumented(self):
        fake = self._fake_module()
        missing = _missing_classes(fake)
        assert "B" in missing
        assert "A" not in missing

    def test_missing_classes_ignores_imported(self):
        fake = self._fake_module()
        missing = _missing_classes(fake)
        assert "Path" not in missing

    def test_missing_functions_finds_undocumented(self):
        fake = self._fake_module()
        missing = _missing_functions(fake)
        assert "fb" in missing
        assert "fa" not in missing


class TestAuditModule:
    def test_hardened_modules_are_clean(self):
        for name in HARDENED_MODULES:
            result = audit_module(name)
            assert result["clean"] is True, f"{name} مو موثّق بالكامل: {result}"
            assert result["module_doc"] is True
            assert result["missing_classes"] == []
            assert result["missing_functions"] == []


class TestAuditAll:
    def test_all_hardened_clean(self):
        report = audit_all()
        assert report["all_clean"] is True
        assert report["modules_checked"] == len(HARDENED_MODULES)
        assert set(report["fully_documented"]) == set(HARDENED_MODULES)
        assert report["incomplete"] == {}

    def test_report_keys(self):
        report = audit_all()
        assert set(report.keys()) == {
            "modules_checked", "fully_documented", "incomplete", "all_clean"
        }

    def test_incomplete_detected_on_fake(self):
        fake = types.ModuleType("fake_incomplete_abc")

        class NoDoc:
            pass

        NoDoc.__module__ = "fake_incomplete_abc"
        fake.NoDoc = NoDoc
        fake.__doc__ = """وحدة"""
        sys.modules["fake_incomplete_abc"] = fake
        try:
            report = audit_all(["fake_incomplete_abc"])
            assert report["all_clean"] is False
            assert "fake_incomplete_abc" in report["incomplete"]
            assert "NoDoc" in report["incomplete"]["fake_incomplete_abc"]["missing_classes"]
        finally:
            sys.modules.pop("fake_incomplete_abc", None)
