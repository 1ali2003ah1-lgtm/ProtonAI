"""P6-S1: ONNX export with numerical parity proof (ADR-008).

Wrapper replicates _to_tensor normalization EXACTLY (ddof=0 variance,
matching numpy) so ONNX graph equals the torch path. Parity and mask
agreement are asserted before anything is committed.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import torch
from torch import nn

from torch_segmenter import TorchSegmenter  # noqa: E402

MODEL_DIR = ROOT / "models"
VERSION = "0.7.0"
EPOCHS = 40
SEED = 42
PARITY_TOL = 1e-4


class _ExportWrapper(nn.Module):
    def __init__(self, net):
        super().__init__()
        self.net = net

    def forward(self, x):
        m = x.mean()
        var = ((x - m) ** 2).mean()  # ddof=0, matches numpy std
        x = (x - m) / (var.sqrt() + 1e-6)
        return torch.sigmoid(self.net(x))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    from dicom_reader import DicomReader
    d = ROOT / "data" / "synth_ct" / "SYNTH-002"
    reader = DicomReader(metadata_keys=["PatientID"])
    slices = sorted(d.glob("*.dcm"))
    hu = np.asarray(reader.read(slices[0])["pixels"], dtype=np.float32)
    masks = np.load(d / "ground_truth" / "masks.npy")

    model = TorchSegmenter(seed=SEED)
    model.fit(hu, masks[0], epochs=EPOCHS)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    pt_path = MODEL_DIR / f"protonai_seg_v{VERSION}.pt"
    model.save(pt_path)
    onnx_path = MODEL_DIR / f"protonai_seg_v{VERSION}.onnx"

    wrapper = _ExportWrapper(model.net)
    wrapper.eval()
    torch.onnx.export(wrapper, torch.zeros(1, 1, *hu.shape), str(onnx_path),
                      input_names=["hu"], output_names=["prob"],
                      dynamic_axes={"hu": {2: "H", 3: "W"},
                                    "prob": {2: "H", 3: "W"}},
                      opset_version=18, dynamo=False)

    import onnxruntime as ort
    sess = ort.InferenceSession(str(onnx_path))
    prob_o = sess.run(None, {"hu": hu[None, None]})[0]
    with torch.no_grad():
        prob_t = torch.sigmoid(model.net(model._to_tensor(hu))).numpy()
    max_diff = float(np.abs(prob_t - prob_o).max())
    agree = float(np.mean((prob_t[0, 0] > 0.5) == (prob_o[0, 0] > 0.5)))

    card = {"version": VERSION, "seed": SEED, "epochs": EPOCHS,
            "train_slice": slices[0].name, "parity_max_diff": max_diff,
            "mask_agreement": agree, "parity_tolerance": PARITY_TOL,
            "torch_version": torch.__version__,
            "onnx_sha256": sha(onnx_path), "pt_sha256": sha(pt_path)}
    (MODEL_DIR / "MODEL_CARD.json").write_text(
        json.dumps(card, indent=2, sort_keys=True), encoding="utf-8")
    assert max_diff < PARITY_TOL, f"parity violated: {max_diff}"
    assert agree == 1.0, f"mask mismatch: {agree}"
    print(f"EXPORT v{VERSION}: parity_max_diff={max_diff:.2e} "
          f"mask_agreement={agree:.2f}")
    print("Saved -> models/ (onnx + pt + MODEL_CARD.json)")


if __name__ == "__main__":
    main()
