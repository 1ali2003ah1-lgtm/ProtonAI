"""P3-S3: schema + consistency guard for external validation artifact."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

ART = Path("external_validation_results.json")


@pytest.fixture
def artifact():
    return json.loads(ART.read_text(encoding="utf-8"))


def test_artifact_exists():
    assert ART.exists()


def test_schema_required_keys(artifact):
    for k in ("protocol", "seeds", "epochs", "baseline",
              "experiment", "statistics", "verdict"):
        assert k in artifact, k
    for m in ("baseline", "experiment"):
        r = artifact[m]
        for d in ("in_domain_SYNTH-001", "in_domain_SYNTH-002",
                  "cross_SYNTH-001_to_SYNTH-002", "cross_SYNTH-002_to_SYNTH-001",
                  "gap_S1_to_S2", "gap_S2_to_S1"):
            assert d in r, f"{m}.{d}"


def test_gaps_in_valid_range(artifact):
    for m in ("baseline", "experiment"):
        for k in ("gap_S1_to_S2", "gap_S2_to_S1"):
            assert -1.0 <= artifact[m][k] <= 1.0


def test_multi_seed_consistency(artifact):
    for m in ("baseline", "experiment"):
        for d in ("in_domain_SYNTH-001", "in_domain_SYNTH-002",
                  "cross_SYNTH-001_to_SYNTH-002", "cross_SYNTH-002_to_SYNTH-001"):
            per_seed = artifact[m][d]["per_seed"]
            assert len(per_seed) == len(artifact["seeds"])
            assert abs(artifact[m][d]["mean"] - np.mean(per_seed)) < 1e-9


def test_verdict_matches_numbers(artifact):
    b, e = artifact["baseline"], artifact["experiment"]
    exp_better_12 = e["gap_S1_to_S2"] < b["gap_S1_to_S2"]
    exp_better_21 = e["gap_S2_to_S1"] < b["gap_S2_to_S1"]
    v = artifact["verdict"]
    if exp_better_12 and exp_better_21:
        assert "generalizes better" in v or "MODERATE" in v
    elif exp_better_12 or exp_better_21:
        assert "MIXED" in v or "generalizes better" in v
    else:
        assert "NO GENERALIZATION ADVANTAGE" in v


def test_statistics_executed(artifact):
    s = artifact["statistics"]
    assert 0.0 <= s["permutation_p_S1toS2"] <= 1.0
    assert 0.0 <= s["permutation_p_S2toS1"] <= 1.0
    assert s["bootstrap_ci_S1toS2"][0] <= s["bootstrap_ci_S1toS2"][1]
    assert s["bootstrap_ci_S2toS1"][0] <= s["bootstrap_ci_S2toS1"][1]
