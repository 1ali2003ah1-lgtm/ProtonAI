"""
ProtonAI - Documentation Check
فحص آلي للتوثيق الداخلي (docstrings) بمعيار PEP257
يضمن أن كل وحدة وكلاس ودالة موثّقة قبل الاعتماد
"""

import inspect
import importlib
import logging
from typing import List, Dict, Any

logger = logging.getLogger("ProtonAI.DocsCheck")

# الوحدات المحصّنة بالمرحلة 1 (يجب أن تكون موثّقة 100%)
HARDENED_MODULES: List[str] = [
    "config",
    "logging_setup",
    "strict_validation",
    "anonymizer",
    "audit",
]


def _doc_present(obj: Any) -> bool:
    """هل للكائن docstring غير فارغ؟"""
    doc = getattr(obj, "__doc__", None)
    return bool(doc and doc.strip())


def _missing_classes(module: Any) -> List[str]:
    """أسماء الكلاسات المعرفة بالوحدة (ليست مستوردة) والناقصة توثيقاً"""
    missing = []
    for name, obj in inspect.getmembers(module, inspect.isclass):
        if getattr(obj, "__module__", None) != module.__name__:
            continue  # مستورد من وحدة أخرى → نتجاهله
        if not _doc_present(obj):
            missing.append(name)
    return missing


def _missing_functions(module: Any) -> List[str]:
    """أسماء الدوال العليا (top-level) الناقصة توثيقاً"""
    missing = []
    for name, obj in inspect.getmembers(module, inspect.isfunction):
        if getattr(obj, "__module__", None) != module.__name__:
            continue
        if not _doc_present(obj):
            missing.append(name)
    return missing


def audit_module(module_name: str) -> Dict[str, Any]:
    """فحص توثيق وحدة واحدة بالاسم"""
    module = importlib.import_module(module_name)
    missing_cls = _missing_classes(module)
    missing_fn = _missing_functions(module)
    module_ok = _doc_present(module)
    clean = module_ok and not missing_cls and not missing_fn
    return {
        "module": module_name,
        "module_doc": module_ok,
        "missing_classes": missing_cls,
        "missing_functions": missing_fn,
        "clean": clean,
    }


def audit_all(module_names: List[str] = None) -> Dict[str, Any]:
    """فحص توثيق مجموعة وحدات وإرجاع تقرير شامل"""
    names = list(module_names) if module_names else list(HARDENED_MODULES)
    results = [audit_module(n) for n in names]
    fully = [r["module"] for r in results if r["clean"]]
    incomplete = {r["module"]: {
        "module_doc": r["module_doc"],
        "missing_classes": r["missing_classes"],
        "missing_functions": r["missing_functions"],
    } for r in results if not r["clean"]}
    report = {
        "modules_checked": len(results),
        "fully_documented": fully,
        "incomplete": incomplete,
        "all_clean": len(incomplete) == 0,
    }
    if report["all_clean"]:
        logger.info(f"كل الوحدات موثّقة بالكامل ({len(fully)} وحدة)")
    else:
        logger.warning(f"وحدات ناقصة التوثيق: {list(incomplete.keys())}")
    return report
