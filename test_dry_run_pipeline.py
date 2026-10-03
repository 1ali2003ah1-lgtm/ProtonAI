"""D3: end-to-end dry-run guard (6 tests, path-safety)."""
from __future__ import annotations

import json
from pathlib import Path

from tools.dry_run_pipeline import (DRAFT, build_synthetic_series, dry_run,
                                    seal_series)

ROOT = Path(__file__).resolve().parent


def test_good_series_accept(tmp_path):
    d = build_synthetic_series(tmp_path / "g")
    r = dry_run(d, tmp_path / "reg.json")
    assert r["verdict"] == "ACCEPT" and r["seals"] == 4


def test_phi_aborts_no_draft(tmp_path):
    d = build_synthetic_series(tmp_path / "b", name="DOE^JOHN")
    r = dry_run(d, tmp_path / "reg.json")
    assert r["verdict"] == "REJECT" and not (tmp_path / "reg.json").exists()


def test_seal_determinism(tmp_path):
    d = build_synthetic_series(tmp_path / "s")
    assert seal_series(d) == seal_series(d)


def test_draft_labeled(tmp_path):
    d = build_synthetic_series(tmp_path / "g2")
    dry_run(d, tmp_path / "reg.json")
    t = DRAFT.read_text(encoding="utf-8")
    assert "DRAFT" in t and "synthetic" in t and "v5.0" in t


def test_register_keys(tmp_path):
    d = build_synthetic_series(tmp_path / "g3")
    dry_run(d, tmp_path / "reg.json")
    r = json.loads((tmp_path / "reg.json").read_text(encoding="utf-8"))
    assert {"verdict", "n_slices", "seals", "mode"} <= set(r)


def test_safety_rpt_untouched(tmp_path):
    rpt = ROOT / "EXPERIMENT_REPORT.md"
    before = rpt.read_text(encoding="utf-8")
    d = build_synthetic_series(tmp_path / "g4")
    dry_run(d, tmp_path / "reg.json")
    assert rpt.read_text(encoding="utf-8") == before
