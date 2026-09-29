"""P6-S1: deployment guard (parity, hashes, contract) - 5 tests."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent
MODELS = ROOT / "models"
ONNX = MODELS / "protonai_seg_v0.7.0.onnx"
PT = MODELS / "protonai_seg_v0.7.0.pt"
CARD = MODELS / "MODEL_CARD.json"


@pytest.fixture(scope="module")
def card():
    return json.loads(CARD.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def hu():
    from dicom_reader import DicomReader
    d = ROOT / "data" / "synth_ct" / "SYNTH-002"
    reader = DicomReader(metadata_keys=["PatientID"])
    return np.asarray(reader.read(sorted(d.glob("*.dcm"))[0])["pixels"],
                      dtype=np.float32)


def test_artifacts_exist():
    assert ONNX.exists() and PT.exists() and CARD.exists()


def test_parity_within_tolerance(card):
    assert card["parity_max_diff"] < card["parity_tolerance"]
    assert card["mask_agreement"] == 1.0


def test_hashes_current(card):
    assert card["onnx_sha256"] == hashlib.sha256(ONNX.read_bytes()).hexdigest()
    assert card["pt_sha256"] == hashlib.sha256(PT.read_bytes()).hexdigest()


def test_contract_matches_torch(hu):
    from inference_contract import run_inference
    from torch_segmenter import TorchSegmenter
    m = TorchSegmenter().load(PT)
    resp = run_inference(hu, ONNX)
    assert np.array_equal(np.array(resp["mask"]), m.segment(hu))


def test_contract_confidence_flag(hu):
    from inference_contract import run_inference
    resp = run_inference(hu, ONNX, vote_entropy=0.0)
    assert "confidence" in resp and resp["review_required"] is False
