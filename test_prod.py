"""W3 TEAM: production infrastructure guard (10 tests)."""
from __future__ import annotations

import re
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent
client = TestClient(__import__("server").app)


def test_ci_workflow():
    t = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "pytest" in t and "cov" in t and "cache: pip" in t


def test_requirements():
    t = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert "fastapi" in t and "pytest-cov" in t


def test_dockerfile_hardened():
    t = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "uvicorn" in t and "USER 1000" in t and "HEALTHCHECK" in t


def test_dockerignore():
    assert (ROOT / ".dockerignore").exists()


def test_makefile():
    t = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert "test:" in t and "coverage:" in t and "docker-run:" in t


def test_pyproject_full():
    t = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "protonai" in t and "[project.scripts]" in t and "urls" in t


def test_version_single_source():
    t = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r'version = "([^"]+)"', t)
    from tools.version import __version__
    assert m and m.group(1) == __version__


def test_cli_entrypoint():
    from tools import cli
    assert callable(cli.main)


def test_health():
    r = client.get("/api/health").json()
    assert r["status"] == "ok" and "version" in r


def test_bad_input_not_500():
    assert client.get("/api/segment?z=abc").status_code in (400, 422)
    assert client.get("/api/segment?z=0").status_code == 200
