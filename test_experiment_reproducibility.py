"""P2-S5: reproducibility, schema & cryptographic integrity guard.

Layers:
1. Verdict agreement across artifacts.
2. Statistical criteria hold in the committed artifact.
3. Cross-artifact numeric consistency.
4. Dice values within valid [0, 1] range.
5. Generator determinism (SYNTH-001 & SYNTH-002, byte-for-byte).
6. Statistics artifact schema validation.
7. Provenance integrity: sha256 of evidence == provenance manifest
   (tamper detection for scientific evidence).
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from make_synthetic_dicom import build_phantom  # noqa: E402

PIPE = ROOT / "pipeline_experiment_synth002.json"
STATS = ROOT / "experiment_statistics_synth002.json"
PROV = ROOT / "docs" / "experiments" / "PROVENANCE_synth002.json"
GT2 = ROOT / "data" / "synth_ct" / "SYNTH-002" / "ground_truth"
GT1 = ROOT / "data" / "synth_ct" / "SYNTH-001" / "ground_truth"


def _load(p):
    return json.loads(p.read_text(encoding="utf-8"))


def _sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_verdicts_agree_and_support():
    pipe, stats = _load(PIPE), _load(STATS)
    assert pipe["verdict"] == "HYPOTHESIS SUPPORTED"
    assert "SUPPORTED" in stats["final_verdict"]


def test_statistical_criteria_hold():
    stats = _load(STATS)
    assert stats["wilcoxon_p_value"] < 0.05
    assert stats["ci_excludes_zero"] is True
    assert all(v == "SUPPORTED" for v in stats["multi_seed_verdicts"])
    assert stats["robust_across_seeds"] is True


def test_cross_artifact_delta_consistency():
    pipe, stats = _load(PIPE), _load(STATS)
    recomputed = float(np.mean(stats["per_case_differences"]))
    assert abs(pipe["delta"] - recomputed) < 1e-9


def test_dice_values_in_valid_range():
    pipe = _load(PIPE)
    for key in ("baseline_per_case", "experiment_per_case"):
        assert all(0.0 <= v <= 1.0 for v in pipe[key]), key


def test_generator_determinism_synth002():
    hu, masks = build_phantom(seed=11, contrast=80.0, noise=25.0, irregular=True)
    assert np.array_equal(hu, np.load(GT2 / "hu.npy"))
    assert np.array_equal(masks, np.load(GT2 / "masks.npy"))


def test_generator_determinism_synth001():
    hu, masks = build_phantom(seed=7)
    assert np.array_equal(hu, np.load(GT1 / "hu.npy"))
    assert np.array_equal(masks, np.load(GT1 / "masks.npy"))


def test_statistics_schema():
    stats = _load(STATS)
    required = ["series", "wilcoxon_p_value", "ci_excludes_zero",
                "multi_seed_verdicts", "robust_across_seeds",
                "final_verdict", "per_case_differences"]
    for key in required:
        assert key in stats, f"missing key: {key}"
    assert len(stats["per_case_differences"]) == 8


def test_provenance_integrity():
    prov = _load(PROV)
    assert prov["hashes"]["pipeline_results"] == _sha(PIPE)
    assert prov["hashes"]["statistics"] == _sha(STATS)
    assert prov["hashes"]["ground_truth/hu.npy"] == _sha(GT2 / "hu.npy")
    assert prov["hashes"]["ground_truth/masks.npy"] == _sha(GT2 / "masks.npy")
