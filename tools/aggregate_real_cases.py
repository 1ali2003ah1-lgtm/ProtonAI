"""D4: multi-case aggregation + v5 promotion gate.

Aggregates per-case deltas (B2/B3) with bootstrap CI + Wilcoxon; applies
a promotion gate reading min_cases from PARTNERSHIP-MANIFEST. Emits an
isolated promotion-decision doc; never modifies EXPERIMENT_REPORT.md.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from dose_stats import bootstrap_ci, verdict_for, wilcoxon_p

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "docs" / "partnership" / "PARTNERSHIP-MANIFEST.json"
DECISION = ROOT / "docs" / "product" / "RPT-001-V5-PROMOTION-DECISION.md"


def min_cases():
    return int(json.loads(MANIFEST.read_text(encoding="utf-8"))["min_cases"])


def aggregate_deltas(x):
    x = np.asarray(x, float)
    lo, hi = bootstrap_ci(x)
    p = wilcoxon_p(x)
    return {"mean": float(x.mean()), "ci_lo": lo, "ci_hi": hi, "p": p,
            "verdict": verdict_for(lo, x.mean(), p)}


def promotion_decision(n, verdict, minc=None):
    minc = minc if minc is not None else min_cases()
    reasons = []
    if n < minc:
        reasons.append(f"n={n} < min_cases={minc}")
    if verdict not in ("SUPERIOR", "NON_INFERIOR"):
        reasons.append(f"verdict {verdict} not sufficient")
    return ("PROMOTE" if not reasons else "HOLD"), reasons


def run_aggregation(d95, oar, out_json):
    agg = {"generated": datetime.now(timezone.utc)
           .strftime("%Y-%m-%d %H:%M UTC"),
           "n_cases": len(d95),
           "d95": aggregate_deltas(d95), "oar_v20": aggregate_deltas(oar)}
    decision, reasons = promotion_decision(agg["n_cases"],
                                           agg["d95"]["verdict"])
    agg["promotion"] = {"decision": decision, "reasons": reasons}
    Path(out_json).write_text(json.dumps(agg, indent=2), encoding="utf-8")
    DECISION.parent.mkdir(parents=True, exist_ok=True)
    DECISION.write_text(f"""# RPT-001 v5.0 Promotion Decision

> Isolated decision record; EXPERIMENT_REPORT.md v4.0 untouched.

- n_cases: {agg['n_cases']} (min_cases={min_cases()})
- D95 verdict: {agg['d95']['verdict']} (mean {agg['d95']['mean']:.3f},
  CI [{agg['d95']['ci_lo']:.3f},{agg['d95']['ci_hi']:.3f}], p={agg['d95']['p']:.4f})
- **Decision: {decision}**
- Reasons: {'; '.join(reasons) or 'none - criteria met'}

## Traceability
EXPERIMENT_REPORT.md v4.0, RPT-001-V5-DRAFT, DOSE-IMPACT-001,
PARTNERSHIP-MANIFEST, tools/aggregate_real_cases.py.
""", encoding="utf-8")
    return agg


if __name__ == "__main__":
    rng = np.random.default_rng(0)
    print(json.dumps(run_aggregation(rng.normal(0.06, 0.02, 10),
                                     rng.normal(0.02, 0.01, 10),
                                     ROOT / "real_aggregate.json"), indent=2))
