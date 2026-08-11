"""
ProtonAI - Restructure Tool (Laptop)
أداة إعادة هيكلة آمنة: تنقل الوحدات الجديدة لحزم (data/physics/models/governance/api)،
تعيد كتابة الاستيرادات، تشغّل الاختبارات، وإذا فشلت ترجّع كل شي تلقائياً (git revert).
الاستخدام:  python restructure_for_laptop.py [--dry-run]
"""

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent

PACKAGES = ["governance", "physics", "models", "data", "api"]

# نقل محدود: الوحدات الجديدة فقط (الـ 90 القديمة تُنقل لاحقاً على لابتوب)
MAPPING = {
    "gov_anonymizer.py": "governance/anonymizer.py",
    "gov_audit_log.py": "governance/audit_log.py",
    "hu_rsp_calibration.py": "physics/hu_rsp_calibration.py",
    "mc_tissue_compare.py": "physics/mc_tissue_compare.py",
    "robustness.py": "physics/robustness.py",
    "uncertainty_aware.py": "models/uncertainty.py",
    "seg_metrics.py": "models/seg_metrics.py",
    "segmentation_train.py": "models/segmentation_train.py",
    "dicom_parser.py": "data/dicom_parser.py",
    "harmonization.py": "data/harmonization.py",
    "api_main.py": "api/main.py",
}

REWRITES = [
    ("from gov_anonymizer import", "from governance.anonymizer import"),
    ("from gov_audit_log import", "from governance.audit_log import"),
    ("from hu_rsp_calibration import", "from physics.hu_rsp_calibration import"),
    ("from mc_tissue_compare import", "from physics.mc_tissue_compare import"),
    ("from robustness import", "from physics.robustness import"),
    ("from uncertainty_aware import", "from models.uncertainty import"),
    ("from seg_metrics import", "from models.seg_metrics import"),
    ("from segmentation_train import", "from models.segmentation_train import"),
    ("from dicom_parser import", "from data.dicom_parser import"),
    ("from harmonization import", "from data.harmonization import"),
    ("from api_main import", "from api.main import"),
]

SKIP = {"restructure_for_laptop.py", "test_restructure_plan.py"}


def apply():
    for pkg in PACKAGES:
        d = ROOT / pkg
        d.mkdir(exist_ok=True)
        init = d / "__init__.py"
        if not init.exists():
            init.write_text(f'"""ProtonAI {pkg} package"""\n', encoding="utf-8")
    for old, new in MAPPING.items():
        src, dst = ROOT / old, ROOT / new
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
    for py in ROOT.rglob("*.py"):
        if py.name in SKIP:
            continue
        text = py.read_text(encoding="utf-8")
        out = text
        for old, new in REWRITES:
            out = out.replace(old, new)
        if out != text:
            py.write_text(out, encoding="utf-8")


def revert():
    subprocess.run(["git", "checkout", "--", "."])
    for pkg in PACKAGES:
        shutil.rmtree(ROOT / pkg, ignore_errors=True)


def main():
    if "--dry-run" in sys.argv:
        for old, new in MAPPING.items():
            print(f"{old} -> {new}")
        return
    apply()
    code = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x"]).returncode
    if code != 0:
        revert()
        print("❌ فشل — تم الإرجاع التلقائي، لا شي تخرب")
        sys.exit(1)
    print("✅ نجح — نفّذ: git add -A && git commit -m 'restructure'")


if __name__ == "__main__":
    main()
