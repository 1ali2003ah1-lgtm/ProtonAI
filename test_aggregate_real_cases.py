"""D4: aggregation + promotion gate guard (6 tests, path-safety)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from tools.aggregate_real_cases import (DECISION, aggregate_deltas,
                                        min_cases, promotion_decision,
                                        run_aggregation)

ROOT = Path(__file__).resolve().parent


def test_aggregate_stats():
    a = aggregate_deltas(np.array([0.05, 0.07, 0.06, 0.08]))
    assert a["ci_lo"] <= a["mean"] <= a["ci_hi"] and 0 <= a["p"] <= 1


def test_gate_hold_when_few_cases():
    d, r = promotion_decision(5, "SUPERIOR")
    assert d == "HOLD" and r


def test_gate_promote_when_complete():
    d, r = promotion_decision(10, "SUPERIOR", minc=10)
    assert d == "PROMOTE" and not r


def test_gate_hold_on_weak_verdict():
    d, r = promotion_decision(10, "NOT_ESTABLISHED", minc=10)
    assert d == "HOLD"


def test_min_cases_from_manifest():
    assert min_cases() == 10


def test_run_and_safety(tmp_path):
    rpt = ROOT / "EXPERIMENT_REPORT.md"
    before = rpt.read_text(encoding="utf-8")
    rng = np.random.default_rng(1)
    agg = run_aggregation(rng.normal(0.06, 0.02, 10),
                          rng.normal(0.02, 0.01, 10),
                          tmp_path / "agg.json")
    assert agg["promotion"]["decision"] in ("PROMOTE", "HOLD")
    t = DECISION.read_text(encoding="utf-8")
    assert "Promotion Decision" in t
    assert rpt.read_text(encoding="utf-8") == before
