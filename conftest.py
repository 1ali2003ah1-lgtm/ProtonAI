"""Session-scoped bootstrap of synthetic DICOM build artifacts.

The .dcm slices are gitignored artifacts (see data/synth_ct/README.md).
Deterministic seeds guarantee byte-identical regeneration, so any fresh
clone can run the ingestion tests without manual steps (CI-ready).
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "tools"))

from make_synthetic_dicom import build_phantom, write_series  # noqa: E402


def _ensure_series(name, **kw):
    out = ROOT / "data" / "synth_ct" / name
    if not list(out.glob("*.dcm")):
        hu, masks = build_phantom(**kw)
        write_series(out, hu, masks, patient_id=name)


@pytest.fixture(scope="session", autouse=True)
def synthetic_series():
    _ensure_series("SYNTH-001")
    _ensure_series("SYNTH-002", seed=11, contrast=80.0, noise=25.0,
                   irregular=True)
