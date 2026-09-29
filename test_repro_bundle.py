"""P6-S4: reproducibility bundle guard (4 tests)."""
from __future__ import annotations

import hashlib
import json
import platform
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BUNDLE = ROOT / "docs" / "experiments" / "REPRO_BUNDLE.json"
BOOT = ROOT / "tools" / "bootstrap_env.sh"


def test_bundle_exists():
    assert BUNDLE.exists() and BOOT.exists()


def test_python_version_recorded():
    b = json.loads(BUNDLE.read_text(encoding="utf-8"))
    assert b["python"] == platform.python_version()


def test_evidence_hashes_current():
    b = json.loads(BUNDLE.read_text(encoding="utf-8"))
    for rel, h in b["evidence_sha256"].items():
        assert hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() == h


def test_bootstrap_covers_known_traps():
    t = BOOT.read_text(encoding="utf-8")
    assert "index-url" in t and "onnxscript" in t and t.startswith("#!")
