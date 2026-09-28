"""P4-S4: executable release gate for v0.5.0-clinical-package.

All checks must pass before tagging; any failure exits non-zero with
RELEASE BLOCKED. This is the machine-enforced Definition of Done.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

CHECKS = []


def check(name, fn):
    try:
        ok, detail = fn()
    except Exception as e:  # noqa: BLE001
        ok, detail = False, f"{type(e).__name__}: {e}"
    CHECKS.append((name, ok, detail))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def git_clean():
    out = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                         capture_output=True, text=True).stdout.strip()
    return out == "", (out or "clean")


def manifest_ok(rel_manifest):
    m = load(ROOT / rel_manifest)
    series_base = ROOT / "data" / "synth_ct" / m.get("series", "")
    bad = []
    logical = {"pipeline_results": "pipeline_experiment_synth002.json",
               "statistics": "experiment_statistics_synth002.json"}
    for rel, h in m["hashes"].items():
        if rel == "slices":
            for n, hh in h.items():
                pth = series_base / n
                if not pth.exists() or sha(pth) != hh:
                    bad.append(f"slices/{n} (missing? regenerate)")
            continue
        base = series_base if rel.startswith("ground_truth/") else ROOT
        pth = base / logical.get(rel, rel)
        if not pth.exists() or sha(pth) != h:
            bad.append(rel)
    return not bad, ("ok" if not bad else f"mismatch: {bad}")


def policy_ok():
    import clinical_gate
    clinical_gate.load_policy()
    return True, "policy evidence hash verified"


def report_ok():
    t = (ROOT / "EXPERIMENT_REPORT.md").read_text(encoding="utf-8")
    ok = "| RPT-001 | 3.0 |" in t and "## 9. Phase 3" in t
    return ok, ("v3.0 + phase-3 section" if ok else "report outdated")


def register_ok():
    t = (ROOT / "docs/quality_system/iso_13485/DATASET_REGISTER.md") \
        .read_text(encoding="utf-8")
    ok = "DATASET-000-SYNTH-REF" in t
    return ok, ("reference row present" if ok else "register not seeded")


def changelog_ok():
    t = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    return "SUPERSEDED" in t, "CI supersession recorded"


def docs_ok():
    need = [ROOT / "docs/quality_system/iso_13485/CLIN-001_UNCERTAINTY_FLAGGING.md",
            ROOT / "docs/quality_system/iso_13485/DATA-ACQ-001_REAL_DATA_ACQUISITION_PLAN.md",
            ROOT / "docs/quality_system/iso_14971/RISK_REGISTER.md",
            ROOT / "docs/quality_system/iso_13485/CAPA_LOG.md"]
    adrs = list((ROOT / "docs/quality_system/iec_62304").glob("ADR-0*.md"))
    missing = [p.name for p in need if not p.exists()]
    ok = not missing and len(adrs) >= 6
    return ok, (f"{len(adrs)} ADRs + controlled docs"
                if ok else f"missing={missing} adrs={len(adrs)}")


def main():
    check("git working tree clean", git_clean)
    check("phase-2 provenance intact",
          lambda: manifest_ok("docs/experiments/PROVENANCE_synth002.json"))
    check("phase-3 provenance intact",
          lambda: manifest_ok("docs/experiments/PROVENANCE_phase3.json"))
    check("CLIN-001 policy integrity", policy_ok)
    check("RPT-001 v3.0 complete", report_ok)
    check("dataset register seeded", register_ok)
    check("CHANGELOG hygiene", changelog_ok)
    check("controlled document set", docs_ok)
    print("===== RELEASE GATE v0.5.0 =====")
    for name, ok, detail in CHECKS:
        print(f"[{'PASS' if ok else 'FAIL'}] {name} - {detail}")
    failed = [c for c in CHECKS if not c[1]]
    if failed:
        raise SystemExit(f"RELEASE BLOCKED: {len(failed)} check(s) failed")
    print("RELEASE READY: v0.5.0-clinical-package")


if __name__ == "__main__":
    main()
