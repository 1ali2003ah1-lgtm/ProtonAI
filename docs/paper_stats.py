"""
ProtonAI - Paper: Live Statistics Generator
يولّد إحصائيات حية من الكود للورقة العلمية.
"""

from pathlib import Path

ROOT = Path(__file__).parent.parent


def count_units() -> int:
    return len([p for p in ROOT.glob("*.py") if not p.name.startswith("test_")])


def count_tests() -> int:
    return len([p for p in ROOT.glob("test_*.py")])


def count_sites() -> int:
    from tumor_sites import SITES
    return len(SITES)


def top_risk() -> dict:
    from fmea import table
    return max(table(), key=lambda t: t["RPN"])


def count_docs() -> int:
    return len(list((ROOT / "docs").glob("*.md")))


def summary() -> dict:
    return {
        "units": count_units(),
        "tests": count_tests(),
        "sites": count_sites(),
        "top_risk_id": top_risk()["id"],
        "top_risk_rpn": top_risk()["RPN"],
        "docs": count_docs(),
    }


if __name__ == "__main__":
    s = summary()
    print(f"- الوحدات: **{s['units']}**")
    print(f"- ملفات الاختبار: **{s['tests']}**")
    print(f"- مواقع الأورام: **{s['sites']}**")
    print(f"- أعلى خطر: **{s['top_risk_id']}** بـ RPN = **{s['top_risk_rpn']}**")
