"""P5-S1: per-case unified confidence analysis + evidence-derived threshold.

threshold_C = min in-domain unified confidence (mirror of CLIN-001 theta).
Validates: no in-domain case flagged; all cross-domain failures flagged.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from confidence_score import (physics_confidence, review_required,  # noqa: E402
                              unified_confidence)

UQ = ROOT / "uq_analysis_results.json"


def load(p):
    return json.loads(p.read_text(encoding="utf-8"))


def main():
    uq = load(UQ)
    ui, ux = uq["in_domain"], uq["cross_domain"]
    c_in = [unified_confidence(u) for u in ui["per_case_uncertainty"]]
    c_x = [unified_confidence(u) for u in ux["per_case_uncertainty"]]
    threshold = min(c_in)
    flags_x = [review_required(c, threshold) for c in c_x]
    fails_x = [d < uq["fail_threshold"] for d in ux["per_case_dice"]]
    captured = all(fl for f, fl in zip(fails_x, flags_x) if f)
    flags_in = [review_required(c, threshold) for c in c_in]

    print("===== UNIFIED CONFIDENCE (ADR-007) =====")
    print(f"physics confidence (E=150MeV, MC 1%): {physics_confidence():.6f}")
    print(f"in-domain : mean_C={sum(c_in)/len(c_in):.6f} min_C={threshold:.6f}")
    print(f"cross-dom : mean_C={sum(c_x)/len(c_x):.6f} "
          f"flags={sum(flags_x)}/{len(c_x)}")
    print(f"in-domain false flags: {sum(flags_in)}")
    print(f"cross failures captured: {captured}")
    verdict = ("CONFIDENCE CALIBRATED"
               if captured and not any(flags_in)
               else "CONFIDENCE NOT CALIBRATED")
    print(f"VERDICT: {verdict}")

    artifact = {"method": "multiplicative conjunction of model (1-H/ln2) and "
                          "physics (1-combined) confidences",
                "energy_mev": 150.0, "target_mc_error": 0.01,
                "physics_confidence": physics_confidence(),
                "threshold_C": threshold,
                "in_domain": {"per_case_confidence": c_in,
                              "mean": sum(c_in) / len(c_in)},
                "cross_domain": {"per_case_confidence": c_x,
                                 "flags": flags_x,
                                 "mean": sum(c_x) / len(c_x)},
                "failures_captured": captured,
                "in_domain_false_flags": int(sum(flags_in)),
                "verdict": verdict}
    (ROOT / "confidence_analysis_results.json").write_text(
        json.dumps(artifact, indent=2), encoding="utf-8")
    print("Saved -> confidence_analysis_results.json")


if __name__ == "__main__":
    main()
