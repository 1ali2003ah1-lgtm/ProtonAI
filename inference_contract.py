"""P6-S1: versioned inference contract (ADR-008), CLIN-001 aware.

run_inference returns mask + mean_prob; with vote_entropy it adds unified
confidence (ADR-007) and the CLIN-001 review flag from the live policy.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
CONTRACT_VERSION = "1.0"


def run_inference(hu, onnx_path, vote_entropy=None):
    import onnxruntime as ort

    sess = ort.InferenceSession(str(onnx_path))
    prob = sess.run(None, {"hu": np.asarray(hu, dtype=np.float32)
                           [None, None]})[0]
    p = prob[0, 0]
    resp = {"contract_version": CONTRACT_VERSION,
            "mask": (p > 0.5).astype(bool).tolist(),
            "mean_prob": float(p.mean())}
    if vote_entropy is not None:
        from confidence_score import review_required, unified_confidence
        pol = json.loads((ROOT / "clin001_policy.json")
                         .read_text(encoding="utf-8"))
        conf = unified_confidence(vote_entropy)
        resp["confidence"] = conf
        resp["review_required"] = bool(review_required(conf, pol["theta"]))
    return resp
