"""
ProtonAI - Configuration Management
الإدارة المركزية لإعدادات المنصة (نقطة تحكم واحدة لكل الإعدادات)
"""

import os
import logging
from pathlib import Path
from dataclasses import dataclass, field

logger = logging.getLogger("ProtonAI.Config")

# القيم المسموحة لمستوى السجلات
VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


@dataclass
class Settings:
    """
    كل إعدادات المنصة بمكان واحد.
    تقرأ من متغيرات البيئة إن وُجدت، وإلا تستخدم القيم الآمنة الافتراضية.
    """
    app_name: str = "ProtonAI"
    log_level: str = "INFO"
    random_seed: int = 42
    clinical_tolerance_gy: float = 3.0
    anonymize_by_default: bool = True

    # المسارات (تُحسب نسبة لمجلد المشروع)
    base_dir: Path = field(default_factory=lambda: Path.cwd())
    data_dir: Path = field(default_factory=lambda: Path.cwd() / "data")
    models_dir: Path = field(default_factory=lambda: Path.cwd() / "models")
    reports_dir: Path = field(default_factory=lambda: Path.cwd() / "reports")

    def __post_init__(self):
        """التحقق من صحة الإعدادات فور إنشائها"""
        # توحيد مستوى السجلات
        self.log_level = str(self.log_level).upper()
        if self.log_level not in VALID_LOG_LEVELS:
            raise ValueError(
                f"مستوى سجلات غير صالح: {self.log_level}. "
                f"المسموح: {sorted(VALID_LOG_LEVELS)}"
            )

        # البذرة عدد صحيح موجب أو صفر
        self.random_seed = int(self.random_seed)
        if self.random_seed < 0:
            raise ValueError("البذرة العشوائية يجب أن تكون >= 0")

        # التسامح السريري موجب
        self.clinical_tolerance_gy = float(self.clinical_tolerance_gy)
        if self.clinical_tolerance_gy <= 0:
            raise ValueError("التسامح السريري يجب أن يكون > 0")

        # تحويل المسارات وتجهيز المجلدات
        self.base_dir = Path(self.base_dir)
        self.data_dir = Path(self.data_dir)
        self.models_dir = Path(self.models_dir)
        self.reports_dir = Path(self.reports_dir)

    def ensure_dirs(self) -> None:
        """إنشاء مجلدات المخرجات إن لم تكن موجودة"""
        for d in (self.data_dir, self.models_dir, self.reports_dir):
            d.mkdir(parents=True, exist_ok=True)
        logger.info("تم تجهيز مجلدات المخرجات")

    def summary(self) -> dict:
        """ملخص الإعدادات (مفيد للتقارير والتدقيق)"""
        return {
            "app_name": self.app_name,
            "log_level": self.log_level,
            "random_seed": self.random_seed,
            "clinical_tolerance_gy": self.clinical_tolerance_gy,
            "anonymize_by_default": self.anonymize_by_default,
        }


def _env_bool(name: str, default: bool) -> bool:
    """قراءة قيمة منطقية من البيئة بأمان"""
    val = os.environ.get(name)
    if val is None:
        return default
    return str(val).strip().lower() in {"1", "true", "yes", "on"}


def load_settings() -> Settings:
    """
    تحميل الإعدادات: البيئة أولاً، ثم الافتراضي.
    هذه الدالة هي الباب الوحيد لدخول الإعدادات للمنصة.
    """
    settings = Settings(
        app_name=os.environ.get("PROTONAI_APP_NAME", "ProtonAI"),
        log_level=os.environ.get("PROTONAI_LOG_LEVEL", "INFO"),
        random_seed=int(os.environ.get("PROTONAI_SEED", "42")),
        clinical_tolerance_gy=float(os.environ.get("PROTONAI_TOLERANCE", "3.0")),
        anonymize_by_default=_env_bool("PROTONAI_ANONYMIZE", True),
    )
    logger.info(f"تم تحميل إعدادات {settings.app_name} (level={settings.log_level})")
    return settings
