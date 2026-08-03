"""
ProtonAI - Test Containerization
فحص هيكلي لملفات الحاويات (البناء الفعلي على الجهاز؛ الـ CI يتحقق من البنية)
"""

from pathlib import Path

ROOT = Path(__file__).parent


def _read(name):
    return (ROOT / name).read_text(encoding="utf-8")


class TestDockerfile:
    def test_exists(self):
        assert (ROOT / "Dockerfile").exists()

    def test_base_image(self):
        t = _read("Dockerfile")
        assert "FROM" in t
        assert "python:3.10-slim" in t

    def test_workdir_and_copy(self):
        t = _read("Dockerfile")
        assert "WORKDIR /app" in t
        assert "COPY requirements.txt" in t
        assert "COPY . ." in t

    def test_install_deps(self):
        assert "RUN pip install" in _read("Dockerfile")

    def test_non_root_user(self):
        t = _read("Dockerfile")
        assert "USER appuser" in t

    def test_healthcheck_and_cmd(self):
        t = _read("Dockerfile")
        assert "HEALTHCHECK" in t
        assert "CMD" in t


class TestCompose:
    def test_exists(self):
        assert (ROOT / "docker-compose.yml").exists()

    def test_service_and_build(self):
        t = _read("docker-compose.yml")
        assert "services:" in t
        assert "protonai:" in t
        assert "build:" in t
        assert "dockerfile: Dockerfile" in t

    def test_restart_policy(self):
        assert "restart:" in _read("docker-compose.yml")


class TestDockerignore:
    def test_exists(self):
        assert (ROOT / ".dockerignore").exists()

    def test_excludes_cache_and_git(self):
        t = _read(".dockerignore")
        assert "__pycache__/" in t
        assert "*.pyc" in t
        assert ".git/" in t
        assert ".pytest_cache/" in t
