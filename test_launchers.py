"""
ProtonAI - Test Device Launchers (فحص وجود ومحتوى سكربتات التشغيل)
"""

from pathlib import Path

ROOT = Path(__file__).parent


class TestLaunchers:
    def test_sh_exists(self):
        assert (ROOT / "launch_device.sh").exists()

    def test_bat_exists(self):
        assert (ROOT / "launch_device.bat").exists()

    def test_sh_installs_and_runs(self):
        t = (ROOT / "launch_device.sh").read_text(encoding="utf-8")
        assert "pip install -r requirements-device.txt" in t
        assert "run_device_all.py" in t
        assert "streamlit run streamlit_dashboard.py" in t

    def test_bat_installs_and_runs(self):
        t = (ROOT / "launch_device.bat").read_text(encoding="utf-8")
        assert "pip install -r requirements-device.txt" in t
        assert "run_device_all.py" in t
        assert "streamlit run streamlit_dashboard.py" in t
