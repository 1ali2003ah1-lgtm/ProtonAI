"""
ProtonAI - Clinical Runner
سكربت تشغيل المنصة على ملف مستشفى حقيقي
يقرأ الملف، يتحقق، ويطلّع تقريراً مفصّلاً بالعربي
"""

import json
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

from clinical_loader import ClinicalDataLoader

logger = logging.getLogger("ProtonAI.ClinicalRunner")


def run_clinical_report(
    file_path: str | Path,
    output_path: Optional[str | Path] = None,
) -> dict:
    """
    تشغيل التحقق على ملف وإرجاع التقرير.
    إذا عُيّن output_path يُحفظ التقرير JSON بجانبه.
    """
    loader = ClinicalDataLoader()
    result = loader.load_and_validate(file_path)

    report = {
        "generated_at": datetime.now().isoformat(),
        "source_file": str(file_path),
        "total": result["total"],
        "valid_count": result["valid_count"],
        "invalid_count": result["invalid_count"],
        "acceptance_rate": result["acceptance_rate"],
        "invalid_details": result["invalid"],
    }

    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        logger.info(f"تم حفظ التقرير في: {out}")

    return report


def _print_summary(report: dict) -> None:
    """طباعة ملخص مقروء على الشاشة"""
    print("=" * 50)
    print("تقرير التحقق من بيانات المستشفى")
    print("=" * 50)
    print(f"الملف         : {report['source_file']}")
    print(f"إجمالي السجلات: {report['total']}")
    print(f"مقبول         : {report['valid_count']}")
    print(f"مرفوض         : {report['invalid_count']}")
    print(f"نسبة القبول   : {report['acceptance_rate']}")
    if report["invalid_details"]:
        print("-" * 50)
        print("تفاصيل المرفوضين:")
        for item in report["invalid_details"]:
            pid = item["record"].get("patient_id", "غير معروف")
            print(f"  - {pid}: {item['reason']}")
    print("=" * 50)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) < 2:
        print("الاستخدام: python run_clinical.py <مسار_الملف> [مسار_التقرير]")
        sys.exit(1)

    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else "clinical_report.json"
    rep = run_clinical_report(src, dst)
    _print_summary(rep)
