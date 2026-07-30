"""
ProtonAI - Test Structured Logging
اختبارات نظام التسجيل المنظّم
"""

import json
import logging
import pytest

from config import Settings
from logging_setup import (
    JSONFormatter,
    setup_logging,
    get_logger,
    TEXT_FORMAT,
)


def _make_record(msg="test message", level=logging.INFO, name="ProtonAI.Test"):
    return logging.LogRecord(
        name=name, level=level, pathname="x.py", lineno=1,
        msg=msg, args=(), exc_info=None,
    )


class TestJSONFormatter:
    def test_produces_valid_json(self):
        out = JSONFormatter().format(_make_record("hello"))
        data = json.loads(out)  # لو مو JSON صالح راح يفشل هنا
        assert data["level"] == "INFO"
        assert data["logger"] == "ProtonAI.Test"
        assert data["message"] == "hello"
        assert "timestamp" in data

    def test_includes_extra_fields(self):
        rec = _make_record("op done")
        rec.patient_id = "P123"  # حقل إضافي
        data = json.loads(JSONFormatter().format(rec))
        assert data["patient_id"] == "P123"

    def test_handles_non_ascii(self):
        data = json.loads(JSONFormatter().format(_make_record("مرحبا بالعالم")))
        assert data["message"] == "مرحبا بالعالم"


class TestSetupLogging:
    def test_default_level_is_info(self):
        lg = setup_logging()
        assert lg.level == logging.INFO
        assert lg.name == "ProtonAI"

    def test_level_from_argument(self):
        lg = setup_logging(level="debug")
        assert lg.level == logging.DEBUG

    def test_level_from_settings(self):
        lg = setup_logging(settings=Settings(log_level="WARNING"))
        assert lg.level == logging.WARNING

    def test_text_formatter_by_default(self):
        lg = setup_logging()
        fmt = lg.handlers[0].formatter
        assert isinstance(fmt, logging.Formatter)
        assert not isinstance(fmt, JSONFormatter)

    def test_json_formatter_when_requested(self):
        lg = setup_logging(json_format=True)
        assert isinstance(lg.handlers[0].formatter, JSONFormatter)

    def test_no_duplicate_handlers_on_repeat(self):
        setup_logging()
        setup_logging()
        lg = logging.getLogger("ProtonAI")
        assert len(lg.handlers) == 1

    def test_propagate_disabled(self):
        lg = setup_logging()
        assert lg.propagate is False

    def test_invalid_level_via_settings_raises(self):
        with pytest.raises(ValueError):
            setup_logging(settings=Settings(log_level="BOGUS"))


class TestGetLogger:
    def test_returns_child_logger(self):
        lg = get_logger("Ingestion")
        assert lg.name == "ProtonAI.Ingestion"

    def test_different_names_different_loggers(self):
        a = get_logger("A")
        b = get_logger("B")
        assert a.name != b.name
