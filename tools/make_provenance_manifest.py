"""P2-S5: cryptographic provenance manifest for a synthetic-series experiment.

Records everything an auditor needs to reproduce or verify the claim:
git commit, interpreter/library versions, seeds/epochs, and sha256 of
ground-truth arrays, DICOM slices and result artifacts. Any later
tampering with the evidence fails test_provenance_integrity.

Usage: python tools/make_provenance_manifest.py [SERIES] [OUT]
"""
from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def git_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                              capture_output=True, text=True,
                              check=True).stdout.strip()
    except Exception:
        return "unknown"


def versions() -> dict:
    import numpy, pydicom, scipy
    out = {"python": platform.python_version(),
           "numpy": numpy.__version__,
           "pydicom": pydicom.__version__,
           "scipy": scipy.__version__}
    try:
        import torch
        out["torch"] = torch.__version__
    except Exception:
        out["torch"] = "absent"
    return out


def main(series: str, out_name: str):
    series_dir = ROOT / "data" / "synth_ct" / series
    gt = series_dir / "ground_truth"
    manifest = {
        "series": series,
        "git_commit": git_commit(),
        "versions": versions(),
        "config": {"seeds": [42, 123, 999], "epochs": 40,
                   "phantom_seed": 11 if series == "SYNTH-002" else 7},
        "hashes": {
            "ground_truth/hu.npy": sha256_file(gt / "hu.npy"),
            "ground_truth/masks.npy": sha256_file(gt / "masks.npy"),
            "slices": {p.name: sha256_file(p)
                       for p in sorted(series_dir.glob("*.dcm"))},
            "pipeline_results": sha256_file(ROOT / "pipeline_experiment_synth002.json"),
            "statistics": sha256_file(ROOT / "experiment_statistics_synth002.json"),
        },
    }
    out = ROOT / out_name
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Saved -> {out}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "SYNTH-002",
         sys.argv[2] if len(sys.argv) > 2 else "docs/experiments/PROVENANCE_synth002.json")
