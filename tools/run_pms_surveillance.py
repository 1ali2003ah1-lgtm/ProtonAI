"""P7-S2: post-market surveillance (PMS-001, ISO 20416) - statistical.

Indicators:
- flag-rate drift: one-sided two-proportion z-test (first run baseline
  vs latest); DRIFT iff p < 0.05 AND delta > 0.10; <3 runs => insufficient.
- current URGENT count > 0 => escalate.
- inter-observer verdict FAIL => escalate.
Composite verdict + mapped action; append-only PMS ledger.
"""
from __future__ import annotations

import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

HIST = ROOT / "clinical_dashboard_history.json"
DASH = ROOT / "clinical_dashboard.json"
IO = ROOT / "inter_observer_study.json"
OUT = ROOT / "pms_surveillance.json"
LEDGER = ROOT / "pms_ledger.json"
DRIFT_ALPHA = 0.05
DRIFT_MIN_DELTA = 0.10
MIN_RUNS = 3


def git_commit():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                              capture_output=True, text=True,
                              check=True).stdout.strip()
    except Exception:
        return "unknown"


def z_drift_verdict(counts, alpha=DRIFT_ALPHA, min_delta=DRIFT_MIN_DELTA):
    if len(counts) < MIN_RUNS:
        return "STABLE (insufficient history)", None
    f1, n1 = counts[0]
    f2, n2 = counts[-1]
    delta = f2 / n2 - f1 / n1
    if delta <= 0:
        return "STABLE", None
    p_pool = (f1 + f2) / (n1 + n2)
    denom = math.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n2))
    if denom == 0:
        return "STABLE", None
    z = delta / denom
    p = 0.5 * (1 - math.erf(z / math.sqrt(2)))
    if p < alpha and delta > min_delta:
        return "DRIFT: recalibration review required", round(p, 6)
    return "STABLE", round(p, 6)


def composite(drift, urgent, io_verdict):
    issues = []
    if drift.startswith("DRIFT"):
        issues.append("flag-rate drift")
    if urgent > 0:
        issues.append("urgent cases")
    if io_verdict == "FAIL":
        issues.append("inter-observer failure")
    if not issues:
        return "SURVEILLANCE: STABLE", "routine monitoring"
    return ("SURVEILLANCE: ESCALATE",
            "; ".join(issues) + " -> open review per PMS-001")


def main():
    hist = json.loads(HIST.read_text(encoding="utf-8")) if HIST.exists() else []
    counts = [(e.get("cross_flagged", round(e["cross_flag_rate"] *
                                             e.get("cross_n", 8))),
               e.get("cross_n", 8)) for e in hist]
    drift, pval = z_drift_verdict(counts)
    dash = json.loads(DASH.read_text(encoding="utf-8")) if DASH.exists() else {}
    urgent = sum(1 for r in dash.get("scopes", {}).get("cross_domain", {})
                 .get("rows", []) if r.get("triage") == "URGENT")
    io = json.loads(IO.read_text(encoding="utf-8")) if IO.exists() else {}
    io_verdict = io.get("verdict", "PASS")
    state, action = composite(drift, urgent, io_verdict)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    out = {"generated": now, "generator_commit": git_commit(),
           "counts": [list(c) for c in counts],
           "drift_verdict": drift, "drift_p": pval,
           "urgent_count": urgent, "io_verdict": io_verdict,
           "state": state, "action": action}
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    ledger = json.loads(LEDGER.read_text(encoding="utf-8")) \
        if LEDGER.exists() else []
    ledger.append(out)
    LEDGER.write_text(json.dumps(ledger[-100:], indent=2), encoding="utf-8")
    print("===== PMS SURVEILLANCE (PMS-001 v2) =====")
    print(f"runs={len(counts)} drift={drift} (p={pval})")
    print(f"urgent={urgent} io={io_verdict}")
    print(f"{state} | action: {action}")
    print("Saved -> pms_surveillance.json + pms_ledger.json")


if __name__ == "__main__":
    main()
