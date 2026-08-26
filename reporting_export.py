"""
ProtonAI - Reporting Export
تصدير تقارير مُخفية الهوية (JSON / نص) للجنة والـ tumor board:
- scrub: يحذف أي حقول PHI تلقائياً.
- to_json / to_text: مخرجات جاهزة للمشاركة الآمنة.
"""

import json

from clinical_report import render_text

PHI_KEYS = {"name", "patient_name", "id", "patient_id", "mrn",
            "birthdate", "birth_date", "address", "phone", "email"}


def scrub(d: dict) -> dict:
    return {k: v for k, v in d.items() if k.lower() not in PHI_KEYS}


def build_export(report: dict, extras: dict = None) -> dict:
    out = scrub(report)
    if extras:
        out.update(scrub(extras))
    return out


def to_json(report: dict, extras: dict = None) -> str:
    return json.dumps(build_export(report, extras),
                      ensure_ascii=False, indent=2)


def to_text(report: dict) -> str:
    return render_text(report)
