"""P5-S1: unified confidence guard (properties + artifact consistency)."""
from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from confidence_score import (LN2, model_confidence, physics_confidence,
                              review_required, unified_confidence)
from mc_uncertainty import MCUncertainty

ART = Path("uq_analysis_results.json")
CONF = Path("confidence_analysis_results.json")


def test_model_confidence_bounds_and_monotonic():
    assert model_confidence(0.0) == 1.0
    assert model_confidence(LN2) == 0.0
    assert model_confidence(0.01) > model_confidence(0.05)


def test_conjunction_is_conservative():
    c = unified_confidence(0.01)
    assert c <= model_confidence(0.01)
    assert c <= physics_confidence()


def test_physics_matches_contract():
    n = MCUncertainty.n_histories_for_target(0.01)
    comp = MCUncertainty().combined_uncertainty(150.0, n)
    assert abs(physics_confidence() - (1.0 - min(1.0, comp["combined"]))) < 1e-12


def test_artifact_schema_and_bounds():
    a = json.loads(CONF.read_text(encoding="utf-8"))
    for k in ("threshold_C", "physics_confidence", "verdict"):
        assert k in a
    for branch in ("in_domain", "cross_domain"):
        assert all(0.0 <= c <= 1.0 for c in a[branch]["per_case_confidence"])


def test_threshold_is_min_in_domain():
    a = json.loads(CONF.read_text(encoding="utf-8"))
    assert a["threshold_C"] == min(a["in_domain"]["per_case_confidence"])


def test_calibration_verdict():
    a = json.loads(CONF.read_text(encoding="utf-8"))
    assert a["failures_captured"] is True
    assert a["in_domain_false_flags"] == 0
    assert a["verdict"] == "CONFIDENCE CALIBRATED"
