"""P6-S4: reproducibility bundle (env versions + evidence hashes)."""
from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

EVIDENCE = ["experiment_statistics_synth002.json",
            "pipeline_experiment_synth002.json",
            "external_validation_results.json",
            "uq_analysis_results.json",
            "confidence_analysis_results.json",
            "inter_observer_study.json",
            "registered_validation_results.json",
            "clin001_policy.json",
            "models/MODEL_CARD.json",
            "EXPERIMENT_REPORT.md"]
OPTIONAL = ["clinical_dashboard.json", "intake_audit.json"]


def ver(mod):
    try:
        m = __import__(mod)
        return getattr(m, "__version__", "unknown")
    except Exception:
        return "missing"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    missing = [e for e in EVIDENCE if not (ROOT / e).exists()]
    if missing:
        raise SystemExit(f"evidence missing: {missing}")
    bundle = {"python": platform.python_version(),
              "git_commit": subprocess.run(
                  ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                  capture_output=True, text=True).stdout.strip(),
              "libs": {m: ver(m) for m in ("numpy", "scipy", "sklearn",
                                           "pydicom", "torch", "onnx",
                                           "onnxruntime")},
              "evidence_sha256": {e: sha(ROOT / e) for e in EVIDENCE},
              "optional_present": {o: (ROOT / o).exists() for o in OPTIONAL}}
    out = ROOT / "docs" / "experiments" / "REPRO_BUNDLE.json"
    out.write_text(json.dumps(bundle, indent=2, sort_keys=True),
                   encoding="utf-8")
    print(f"REPRO BUNDLE: {len(EVIDENCE)} evidence hashes + env versions")
    print("Saved -> docs/experiments/REPRO_BUNDLE.json")


if __name__ == "__main__":
    main()
