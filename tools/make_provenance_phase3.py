"""P4-S1: seal Phase-3 evidence artifacts with sha256."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILES = ["external_validation_results.json",
         "uq_analysis_results.json",
         "tools/run_external_validation.py",
         "tools/run_uq_analysis.py",
         "real_data_adapter.py",
         "docs/quality_system/iec_62304/ADR-005_EXTERNAL_VALIDATION.md",
         "docs/quality_system/iec_62304/ADR-006_UQ_METHODOLOGY.md"]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def git_commit():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                              capture_output=True, text=True,
                              check=True).stdout.strip()
    except Exception:
        return "unknown"


def main():
    manifest = {"git_commit": git_commit(),
                "hashes": {f: sha(ROOT / f) for f in FILES}}
    out = ROOT / "docs" / "experiments" / "PROVENANCE_phase3.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2, sort_keys=True),
                   encoding="utf-8")
    print(f"Saved -> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
