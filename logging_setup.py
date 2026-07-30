"""
ProtonAI - Structured Logging
نظام تسجيل منظّم: صيغة موحّدة + خيار JSON للتدقيق الآلي
يقرأ مستوى السجلات من وحدة الإعدادات (config)
"""

import json
import logging
from typing import Optional

from config import Settings, load_settings

# الصيغة النصية الموحّدة (مقروءة للبشر)
TEXT_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"

# الحقول المحجوزة بـ LogRecord (ما نكررها كحقول إضافية بالـ JSON)
_RESERVED = {
    "args", "asctime", "created", "exc_info", "exc_text", "filename",
    "funcName", "levelname", "levelno", "lineno", "module", "msecs",
    "message", "msg", "name", "pathname", "process", "processName",
    "relativeCreated", "stack_info", "thread", "threadName",
}


class JSONFormatter(logging.Formatter):
    """مُنسّق يُخرج كل سجل كسطر JSON صالح (machine-readable)"""

    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "timestamp": self.formatTime(record, DATE_FORMAT),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0] is not None:
            log_record["exception"] = self.formatException(record.exc_info)

        # إضافة الحقول الإضافية (extra=...) إن وُجدت
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                log_record[key] = value

        return json.dumps(log_record, ensure_ascii=False, default=str)


def setup_logging(
    level: Optional[str] = None,
    json_format: bool = False,
    settings: Optional[Settings] = None,
) -> logging.Logger:
    """
    تهيئة نظام التسجيل لمنصة ProtonAI.
    - يقرأ المستوى من settings إن مُرّر، وإلا من level، وإلا INFO.
    - يمسح المُعالجات القديمة لتجنب التكرار عند الاستدعاء المتكرر.
    - يعزل سجلات المنصة (propagate=False) لتجنب التسرب.
    """
    if settings is not None:
        level = settings.log_level
    if level is None:
        level = "INFO"
    level = str(level).upper()

    app_logger = logging.getLogger("ProtonAI")
    app_logger.setLevel(level)

    # منع تكرار المُعالجات
    app_logger.handlers.clear()

    handler = logging.StreamHandler()
    handler.setLevel(level)
    handler.setFormatter(JSONFormatter() if json_format else logging.Formatter(TEXT_FORMAT, datefmt=DATE_FORMAT))
    app_logger.addHandler(handler)
    app_logger.propagate = False

    return app_logger


def get_logger(name: str) -> logging.Logger:
    """إرجاع مسجّل فرعي تحت مظلة ProtonAI"""
    return logging.getLogger(f"ProtonAI.{name}")
