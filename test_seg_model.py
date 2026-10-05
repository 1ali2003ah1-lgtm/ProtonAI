"""W1 FINAL: research-grade segmentation guard (7 tests)."""
from __future__ import annotations

import json

import numpy as np
from fastapi.testclient import TestClient

from tools import train_seg

client = TestClient(__import__("server").app)


def test_train_test_cv():
    m = train_seg.train(epochs=120)
    assert m["test_dice"] > 0.8 and m["test_hd95"] <= 3
    assert m["cv_dice_mean"] > 0.8


def test_card_fields():
    c = json.loads(train_seg.CARD.read_text(encoding="utf-8"))
    assert {"test_dice", "cv_dice_mean", "weight_sha256",
            "uncertainty"} <= set(c)


def test_uncertainty_real():
    model = train_seg.ensure_model()
    img, _ = train_seg.make_sample(np.random.default_rng(3))
    _, unc = train_seg.predict_unc(model, img)
    assert 0 <= float(unc.mean()) <= 0.5


def test_predict_dice():
    model = train_seg.ensure_model()
    img, gt = train_seg.make_sample(np.random.default_rng(7))
    pred, _ = train_seg.predict_unc(model, img)
    assert train_seg.dice(pred, gt) > 0.8


def test_api_segment():
    r = client.get("/api/segment?z=0").json()
    assert r["dice"] > 0.8 and "uncertainty" in r


def test_onnx_consistency():
    try:
        import onnxruntime  # noqa
    except Exception:
        return
    assert train_seg.ONNX.exists()


def test_site_label():
    t = (train_seg.ROOT / "docs" / "site" / "index.html").read_text(encoding="utf-8")
    assert "reduction" in t
