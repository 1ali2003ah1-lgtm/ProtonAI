"""
ProtonAI - Reproducibility Package
حزمة التكرار للمحكّمين: بذور + إصدارات + تشيكسام SHA256 للبيانات
أي قارئ يقدر يعيد النتائج ويتأكد إن بياناته مطابقة تماماً (verify)
تُصدَّر كـ JSON ملحق بالورقة العلمية
"""

import json
import hashlib
import logging
import platform
import importlib.metadata
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Iterable

logger = logging.getLogger("ProtonAI.Reproducibility")

# المكتبات المفتاحية اللي نسجل إصدارها (إن وُجدت)
_KEY_LIBS = ("numpy", "scikit-learn", "pydicom", "pandas")


class ReproducibilityPackage:
    """
    حزمة تكرار.
    - add_seed / add_file_checksum / add_bytes_checksum: تجميع.
    - record_versions: بايثون + المكتبات (بأمان، بدون انهيار).
    - build_manifest / save / load: تصدير واستيراد JSON.
    - verify_file / verify_all: إعادة الفحص ضد البصمات المحفوظة.
    """

    def __init__(self, seeds: Optional[Iterable[int]] = None):
        self.seeds: List[int] = list(seeds) if seeds else []
        self.checksums: Dict[str, str] = {}
        self.versions: Dict[str, str] = {}

    def add_seed(self, seed: int) -> None:
        """تسجيل بذرة"""
        self.seeds.append(int(seed))

    def record_versions(self) -> Dict[str, str]:
        """تسجيل إصدار بايثون + المكتبات المفتاحية (بأمان)"""
        self.versions["python"] = platform.python_version()
        for lib in _KEY_LIBS:
            try:
                self.versions[lib] = importlib.metadata.version(lib)
            except Exception:
                continue  # مكتبة غير مثبتة → نتجاوز بدون انهيار
        return self.versions

    @staticmethod
    def _sha256(data: bytes) -> str:
        """بصمة SHA256 سداسية عشر"""
        return hashlib.sha256(data).hexdigest()

    def add_bytes_checksum(self, name: str, data: bytes) -> str:
        """تسجيل بصمة بيانات خام"""
        h = self._sha256(data)
        self.checksums[name] = h
        return h

    def add_file_checksum(self, path) -> str:
        """تسجيل بصمة ملف (بالاسم)"""
        p = Path(path)
        h = self._sha256(p.read_bytes())
        self.checksums[p.name] = h
        return h

    def build_manifest(self) -> Dict[str, Any]:
        """القاموس الكامل للحزمة"""
        return {
            "seeds": list(self.seeds),
            "versions": dict(self.versions),
            "checksums": dict(self.checksums),
            "generated_at": datetime.now().isoformat(),
        }

    def save(self, path) -> Path:
        """حفظ الحزمة كـ JSON"""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.build_manifest(), f, ensure_ascii=False, indent=2)
        logger.info(f"حُفظت حزمة التكرار في: {path}")
        return path

    @classmethod
    def load(cls, path) -> "ReproducibilityPackage":
        """استيراد حزمة من JSON"""
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        pkg = cls(seeds=d.get("seeds", []))
        pkg.versions = dict(d.get("versions", {}))
        pkg.checksums = dict(d.get("checksums", {}))
        return pkg

    def verify_file(self, path) -> bool:
        """هل بصمة الملف الحالي تطابق المحفوظ؟"""
        p = Path(path)
        stored = self.checksums.get(p.name)
        if stored is None:
            return False
        return self._sha256(p.read_bytes()) == stored

    def verify_all(self, paths: Iterable) -> Dict[str, bool]:
        """فحص مجموعة ملفات ضد البصمات"""
        return {Path(p).name: self.verify_file(p) for p in paths}
