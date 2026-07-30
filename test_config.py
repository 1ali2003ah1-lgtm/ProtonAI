"""
ProtonAI - Test Configuration
اختبارات الإدارة المركزية للإعدادات
"""

import os
import pytest
from config import Settings, load_settings, VALID_LOG_LEVELS


class TestSettingsDefaults:
    def test_default_values(self):
        s = Settings()
        assert s.app_name == "ProtonAI"
        assert s.log_level == "INFO"
        assert s.random_seed == 42
        assert s.clinical_tolerance_gy == 3.0
        assert s.anonymize_by_default is True

    def test_paths_are_path_objects(self):
        s = Settings()
        from pathlib import Path
        assert isinstance(s.data_dir, Path)
        assert isinstance(s.models_dir, Path)
        assert isinstance(s.reports_dir, Path)

    def test_log_level_normalized_to_upper(self):
        s = Settings(log_level="debug")
        assert s.log_level == "DEBUG"


class TestSettingsValidation:
    def test_invalid_log_level_raises(self):
        with pytest.raises(ValueError):
            Settings(log_level="NOT_A_LEVEL")

    def test_negative_seed_raises(self):
        with pytest.raises(ValueError):
            Settings(random_seed=-1)

    def test_zero_tolerance_raises(self):
        with pytest.raises(ValueError):
            Settings(clinical_tolerance_gy=0.0)

    def test_negative_tolerance_raises(self):
        with pytest.raises(ValueError):
            Settings(clinical_tolerance_gy=-1.0)

    def test_all_valid_log_levels_accepted(self):
        for level in VALID_LOG_LEVELS:
            s = Settings(log_level=level)
            assert s.log_level == level


class TestSettingsHelpers:
    def test_ensure_dirs_creates_folders(self, tmp_path):
        s = Settings(
            data_dir=tmp_path / "d",
            models_dir=tmp_path / "m",
            reports_dir=tmp_path / "r",
        )
        s.ensure_dirs()
        assert s.data_dir.exists()
        assert s.models_dir.exists()
        assert s.reports_dir.exists()

    def test_summary_contains_keys(self):
        s = Settings()
        summ = s.summary()
        assert "app_name" in summ
        assert "random_seed" in summ
        assert "clinical_tolerance_gy" in summ


class TestLoadSettings:
    def test_load_defaults_when_no_env(self, monkeypatch):
        for key in ["PROTONAI_APP_NAME", "PROTONAI_LOG_LEVEL",
                    "PROTONAI_SEED", "PROTONAI_TOLERANCE", "PROTONAI_ANONYMIZE"]:
            monkeypatch.delenv(key, raising=False)
        s = load_settings()
        assert s.random_seed == 42

    def test_load_from_env(self, monkeypatch):
        monkeypatch.setenv("PROTONAI_SEED", "99")
        monkeypatch.setenv("PROTONAI_LOG_LEVEL", "warning")
        monkeypatch.setenv("PROTONAI_ANONYMIZE", "false")
        s = load_settings()
        assert s.random_seed == 99
        assert s.log_level == "WARNING"
        assert s.anonymize_by_default is False
