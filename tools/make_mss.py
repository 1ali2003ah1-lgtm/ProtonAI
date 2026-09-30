"""A4: market strategy as code (MSS-001).

Competitors, differentiation moat, pricing tiers, GTM phases.
Planning estimates are explicitly labeled (honesty guard).
"""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT = ROOT / "docs" / "product" / "MSS-001_MARKET_STRATEGY.md"

MARKET = ("~300 proton therapy centers worldwide (growing); AI "
          "segmentation market estimated in the billions by 2030. "
          "Figures are planning ESTIMATES - verify before investor use.")

COMPETITORS = [
    {"name": "Varian Eclipse / Ethos",
     "strength": "installed base, integrated TPS",
     "weakness": "closed; no transparent evidence chain",
     "edge": "open sealed evidence + unified confidence"},
    {"name": "RaySearch RayStation",
     "strength": "strong auto-segmentation reputation",
     "weakness": "closed methodology; no exposed PMS loop",
     "edge": "transparency + closed feedback loop"},
    {"name": "Limbus AI",
     "strength": "fast contouring AI",
     "weakness": "no physics-confidence integration",
     "edge": "AI x physics unified score (ADR-007)"},
    {"name": "Mirada / workflow tools",
     "strength": "workflow integration",
     "weakness": "no proton-specific dose linkage",
     "edge": "interactive what-if dose engine"},
]

PRICING = [
    {"tier": "Academic", "price": "free / research",
     "includes": "full open platform"},
    {"tier": "Pilot", "price": "$0 first 10 cases",
     "includes": "onboarding + PMS wall"},
    {"tier": "Clinical SaaS", "price": "per-seat annual + per-patient",
     "includes": "NEXUS console + support"},
    {"tier": "Enterprise", "price": "custom",
     "includes": "federated + PACS + SLA"},
]

GT_PHASES = [
    {"phase": 1, "focus": "academic credibility",
     "actions": "2-3 papers (SVP-001), conference talks",
     "kpi": "papers accepted"},
    {"phase": 2, "focus": "regional pilots (MENA)",
     "actions": "cancer-center pilots, first 10 cases free",
     "kpi": "3 pilot sites"},
    {"phase": 3, "focus": "regulated markets",
     "actions": "FDA 510(k) / CE MDR (REG-001)", "kpi": "clearance"},
    {"phase": 4, "focus": "global network",
     "actions": "federated console + enterprise", "kpi": "revenue/patient"},
]


def git_commit():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                              capture_output=True, text=True,
                              check=True).stdout.strip()
    except Exception:
        return "unknown"


def main():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = ["# MSS-001: Market Strategy", "",
             "## Document Control",
             "| ID | Version | Generated | Generator commit | Status |",
             "|---|---|---|---|---|",
             f"| MSS-001 | 1.0 | {now} | {git_commit()} | EFFECTIVE |", "",
             "## 1. Market", f"{MARKET}", "",
             "## 2. Competitive Landscape",
             "| Competitor | Strength | Weakness | Our edge |",
             "|---|---|---|---|"]
    for c in COMPETITORS:
        lines.append(f"| {c['name']} | {c['strength']} | {c['weakness']} | "
                     f"{c['edge']} |")
    lines += ["", "## 3. Differentiation Moat",
              "- Sealed, open evidence chain (schema v2) - trust by audit.",
              "- Unified confidence = AI x physics (ADR-007).",
              "- Closed PMS feedback loop (PMS-001) - self-improving.",
              "- Interactive what-if dose engine (NEXUS).",
              "- Arabic/English native i18n - regional signature.", "",
              "## 4. Pricing",
              "| Tier | Price | Includes |", "|---|---|---|"]
    for p in PRICING:
        lines.append(f"| {p['tier']} | {p['price']} | {p['includes']} |")
    lines += ["", "## 5. Go-To-Market Phases",
              "| Phase | Focus | Actions | KPI |", "|---|---|---|---|"]
    for g in GT_PHASES:
        lines.append(f"| {g['phase']} | {g['focus']} | {g['actions']} | "
                     f"{g['kpi']} |")
    lines += ["", "## 6. Honesty Note",
              "All market sizes are planning estimates; regulatory and "
              "clinical claims gated by SVP-001 and REG-001 evidence.", "",
              "## 7. Traceability",
              "NEXUS-PRD-001, SVP-001, REG-001, PMS-001, ADR-007.", ""]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"MSS-001: competitors={len(COMPETITORS)} tiers={len(PRICING)} "
          f"gtm_phases={len(GT_PHASES)}")
    print("Saved -> docs/product/MSS-001_MARKET_STRATEGY.md")


if __name__ == "__main__":
    main()
