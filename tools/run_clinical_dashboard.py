"""P7-S1: clinical decision dashboard (CLIN-002) - triage edition.

Per case: entropy, unified confidence, flag, triage (AUTO/REVIEW/URGENT),
review path. URGENT = entropy >= max cross-domain FAILING entropy
(worse than worst known failure). Executive KPIs + append-only run
history (last 50) for drift monitoring (PMS, P7-S2). Additive only.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from clinical_gate import batch_decision  # noqa: E402

UQ = ROOT / "uq_analysis_results.json"
CONF = ROOT / "confidence_analysis_results.json"
POL = ROOT / "clin001_policy.json"
OUT_JSON = ROOT / "clinical_dashboard.json"
HIST = ROOT / "clinical_dashboard_history.json"
OUT_MD = ROOT / "docs" / "quality_system" / "iso_13485" / \
    "CLIN-002_CLINICAL_DASHBOARD.md"


def load(p):
    return json.loads(p.read_text(encoding="utf-8"))


def git_commit():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                              capture_output=True, text=True,
                              check=True).stdout.strip()
    except Exception:
        return "unknown"


def urgent_threshold(uq):
    ux = uq["cross_domain"]
    fails = [d < uq["fail_threshold"] for d in ux["per_case_dice"]]
    fu = [u for u, f in zip(ux["per_case_uncertainty"], fails) if f]
    return max(fu) if fu else None


def main():
    uq, conf, pol = load(UQ), load(CONF), load(POL)
    theta = pol["theta"]
    urgent = urgent_threshold(uq)
    scopes = {}
    for scope in ("in_domain", "cross_domain"):
        ents = uq[scope]["per_case_uncertainty"]
        confs = conf[scope]["per_case_confidence"]
        rows = []
        for i, (e, c) in enumerate(zip(ents, confs)):
            flag = e > theta
            triage = ("AUTO" if not flag else
                      ("URGENT" if (urgent is not None and e >= urgent)
                       else "REVIEW"))
            rows.append({"case": f"{scope}-{i}", "vote_entropy": e,
                         "confidence": c, "flag": flag, "triage": triage,
                         "review": "auto" if triage == "AUTO" else "physicist"})
        flags = [r["flag"] for r in rows]
        scopes[scope] = {"rows": rows, "flagged": int(sum(flags)),
                         "batch_state": batch_decision(flags)}
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    kpis = {"physics_confidence": conf["physics_confidence"],
            "threshold_C": conf["threshold_C"], "theta_entropy": theta,
            "separation_margin": pol.get("separation_margin"),
            "failures_captured": conf["failures_captured"],
            "urgent_entropy": urgent,
            "cross_flag_rate": scopes["cross_domain"]["flagged"] /
            len(scopes["cross_domain"]["rows"])}
    out = {"generated": now, "generator_commit": git_commit(),
           "kpis": kpis, "scopes": scopes}
    OUT_JSON.write_text(json.dumps(out, indent=2), encoding="utf-8")
    hist = json.loads(HIST.read_text(encoding="utf-8")) if HIST.exists() else []
    hist.append({"generated": now,
                 "cross_flag_rate": kpis["cross_flag_rate"],
                 "batch_states": {s: v["batch_state"]
                                  for s, v in scopes.items()}})
    HIST.write_text(json.dumps(hist[-50:], indent=2), encoding="utf-8")

    lines = ["# CLIN-002: Clinical Decision Dashboard", "",
             "## Document Control",
             "| ID | Version | Generated | Generator commit | Status |",
             "|---|---|---|---|---|",
             f"| CLIN-002 | 2.0 | {now} | {git_commit()} | EFFECTIVE |", "",
             "## 1. Executive KPIs",
             "| KPI | Value |",
             "|---|---|",
             f"| physics confidence | {kpis['physics_confidence']:.6f} |",
             f"| theta (entropy) | {theta:.6f} |",
             f"| threshold C | {kpis['threshold_C']:.6f} |",
             f"| separation margin | {kpis['separation_margin']} |",
             f"| failures captured | {kpis['failures_captured']} |",
             f"| urgent entropy | {urgent if urgent else 'n/a'} |",
             f"| cross flag rate | {kpis['cross_flag_rate']:.2f} |", "",
             "## 2. Batch decision states",
             "| Scope | Cases | Flagged | Batch state |",
             "|---|---|---|---|"]
    for scope, s in scopes.items():
        lines.append(f"| {scope} | {len(s['rows'])} | {s['flagged']} | "
                     f"{s['batch_state']} |")
    lines += ["", "## 3. Per-case triage (cross-domain)",
              "| Case | entropy | confidence | flag | triage | review |",
              "|---|---|---|---|---|---|"]
    for r in scopes["cross_domain"]["rows"]:
        lines.append(f"| {r['case']} | {r['vote_entropy']:.6f} | "
                     f"{r['confidence']:.6f} | {r['flag']} | {r['triage']} | "
                     f"{r['review']} |")
    lines += ["", "## 4. Traceability",
              "CLIN-001 (flagging), ADR-006 (UQ), ADR-007 (confidence),",
              "RPT-001 v4.0; history: clinical_dashboard_history.json.", ""]
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print("===== CLINICAL DASHBOARD (CLIN-002 v2) =====")
    print(f"KPIs: theta={theta:.6f} urgent={urgent if urgent else 'n/a'} "
          f"captured={kpis['failures_captured']}")
    for scope, s in scopes.items():
        print(f"{scope}: flagged={s['flagged']}/{len(s['rows'])} "
              f"state={s['batch_state']}")
    print("Saved -> dashboard json + history + CLIN-002 md")


if __name__ == "__main__":
    main()
