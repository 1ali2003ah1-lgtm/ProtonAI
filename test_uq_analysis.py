"""P3-S4: schema + consistency guard for the UQ artifact."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ART = Path("uq_analysis_results.json")


@pytest.fixture
def art():
    return json.loads(ART.read_text(encoding="utf-8"))


def test_artifact_exists():
    assert ART.exists()


def test_schema(art):
    for k in ("method", "seeds", "epochs", "in_domain", "cross_domain",
              "ood_mannwhitney_p", "verdict"):
        assert k in art
    for b in ("in_domain", "cross_domain"):
        for k in ("mean_uncertainty", "spearman_rho", "spearman_p",
                  "per_case_uncertainty", "per_case_dice"):
            assert k in art[b]


def test_uncertainty_nonnegative(art):
    for b in ("in_domain", "cross_domain"):
        assert art[b]["mean_uncertainty"] >= 0.0
        assert all(u >= 0.0 for u in art[b]["per_case_uncertainty"])


def test_dice_in_range(art):
    for b in ("in_domain", "cross_domain"):
        assert all(0.0 <= d <= 1.0 for d in art[b]["per_case_dice"])


def test_verdict_consistency(art):
    inf, ood, v = art["informative"], art["ood_sensitive"], art["verdict"]
    if inf and ood:
        assert "INFORMATIVE" in v and "OOD-SENSITIVE" in v
    elif inf:
        assert v.startswith("UNCERTAINTY INFORMATIVE")
    elif ood:
        assert v.startswith("OOD-SENSITIVE ONLY")
    else:
        assert v == "UNCERTAINTY NOT INFORMATIVE"
