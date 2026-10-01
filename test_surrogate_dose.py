"""B4 FINAL: surrogate dose engine guard (6 tests)."""
from __future__ import annotations

import json

import pytest
import torch

from surrogate_dose import (DoseMLP, MODEL_PATH, REPORT, measure_speedup,
                             prove_parity, train_surrogate)


@pytest.fixture(scope="module")
def trained():
    return train_surrogate(n_samples=200, epochs=60, seed=42)


def test_model_saved(trained):
    model, X, Y = trained
    assert MODEL_PATH.exists()
    assert sum(p.numel() for p in model.parameters()) > 0


def test_parity_numerical(trained):
    model, X, Y = trained
    p = prove_parity(model, X, Y)
    assert p["correlation"] > 0.9 and p["mean_diff"] < 0.15


def test_speedup(trained):
    model, _, _ = trained
    assert measure_speedup(model, n=10) > 1.0


def test_forward_shape():
    y = DoseMLP()(torch.randn(2, 60 * 40))
    assert y.shape == (2, 60 * 40)


def test_report_artifact(trained):
    from surrogate_dose import main
    main()
    r = json.loads(REPORT.read_text(encoding="utf-8"))
    assert {"correlation", "mean_diff", "max_diff", "speedup"} <= set(r)


def test_deterministic_training():
    a = prove_parity(*train_surrogate(50, 10, seed=7)[0:2] +
                     (train_surrogate(50, 10, seed=7)[1],))
    b = prove_parity(*train_surrogate(50, 10, seed=7)[0:2] +
                     (train_surrogate(50, 10, seed=7)[1],))
    assert abs(a["correlation"] - b["correlation"]) < 1e-6
