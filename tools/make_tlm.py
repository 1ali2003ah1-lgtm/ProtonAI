"""A7 enhanced: self-auditing traceability link matrix (TLM-001 v2).

Discovers doc->doc links from actual text; enforces required links,
per-doc sibling coverage, core-asset coverage; fingerprints every doc
(sha256). Any gap refuses generation.
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT = ROOT / "docs" / "product" / "TLM-001_TRACEABILITY_MATRIX.md"

DOCS = {
    "NEXUS-PRD-001": ROOT / "docs" / "product" / "NEXUS-PRD-001.md",
    "PRM-001": ROOT / "docs" / "quality_system" / "iso_13485" /
               "PRM-001_PRODUCT_RISK.md",
    "USP-001": ROOT / "docs" / "quality_system" / "iso_13485" /
               "USP-001_USE_SPECIFICATION.md",
    "MSS-001": ROOT / "docs" / "product" / "MSS-001_MARKET_STRATEGY.md",
    "SVP-001": ROOT / "docs" / "product" /
               "SVP-001_SCIENTIFIC_VALIDATION.md",
    "REG-001": ROOT / "docs" / "product" /
               "REG-001_REGULATORY_STRATEGY.md",
}

REQUIRED_LINKS = [
    ("PRM-001", "NEXUS-PRD-001"), ("USP-001", "PRM-001"),
    ("USP-001", "NEXUS-PRD-001"), ("MSS-001", "NEXUS-PRD-001"),
    ("MSS-001", "SVP-001"), ("MSS-001", "REG-001"),
    ("SVP-001", "NEXUS-PRD-001"), ("SVP-001", "PRM-001"),
    ("SVP-001", "MSS-001"), ("REG-001", "PRM-001"),
    ("REG-001", "USP-001"), ("REG-001", "SVP-001"),
    ("REG-001", "NEXUS-PRD-001"), ("NEXUS-PRD-001", "PRM-001"),
    ("NEXUS-PRD-001", "USP-001"), ("NEXUS-PRD-001", "MSS-001"),
    ("NEXUS-PRD-001", "SVP-001"), ("NEXUS-PRD-001", "REG-001"),
]

REQUIRED_COVERAGE = {
    "NEXUS-PRD-001": {"PRM-001", "USP-001", "MSS-001", "SVP-001", "REG-001"},
    "REG-001": {"PRM-001", "USP-001", "SVP-001"},
    "USP-001": {"PRM-001"},
}

CORE_ASSETS = ["CLIN-001", "CLIN-002", "ADR-006", "ADR-007", "ADR-008",
               "PMS-001", "RPT-001", "PLAYBOOK-001"]


def sha12(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:12]


def git_commit():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                              capture_output=True, text=True,
                              check=True).stdout.strip()
    except Exception:
        return "unknown"


def main():
    missing = [n for n, p in DOCS.items() if not p.exists()]
    if missing:
        raise SystemExit(f"controlled docs missing: {missing}")
    texts = {n: p.read_text(encoding="utf-8") for n, p in DOCS.items()}
    discovered = {s: {t for t in DOCS if t != s and t in texts[s]}
                  for s in DOCS}
    for src, tgt in REQUIRED_LINKS:
        if tgt not in discovered[src]:
            raise SystemExit(f"required link missing: {src} -> {tgt}")
    for doc, req in REQUIRED_COVERAGE.items():
        gap = req - discovered[doc]
        if gap:
            raise SystemExit(f"coverage gap: {doc} missing {sorted(gap)}")
    asset_cov = {a: [s for s in DOCS if a in texts[s]] for a in CORE_ASSETS}
    uncovered = [a for a, c in asset_cov.items() if not c]
    if uncovered:
        raise SystemExit(f"core assets uncovered: {uncovered}")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = ["# TLM-001: Traceability Link Matrix", "",
             "## Document Control",
             "| ID | Version | Generated | Generator commit | Status |",
             "|---|---|---|---|---|",
             f"| TLM-001 | 2.0 | {now} | {git_commit()} | EFFECTIVE |", "",
             "## 1. Method",
             "Links are DISCOVERED from source text; required links and "
             "sibling coverage are enforced; core assets must be covered; "
             "docs fingerprinted (sha256-12). Gaps refuse generation.", "",
             "## 2. Discovered Document-to-Document Matrix",
             "| Source | " + " | ".join(DOCS) + " |",
             "|---|" + "---|" * len(DOCS)]
    for src in DOCS:
        cells = ["✓" if t in discovered[src] else "·" for t in DOCS]
        lines.append(f"| {src} | " + " | ".join(cells) + " |")
    lines += ["", "## 3. Required Links (enforced)",
              "- " + "; ".join(f"{s}->{t}" for s, t in REQUIRED_LINKS), "",
              "## 4. Core-Asset Coverage",
              "| Asset | Referenced by |", "|---|---|"]
    for a, cov in asset_cov.items():
        lines.append(f"| {a} | {', '.join(cov)} |")
    lines += ["", "## 5. Document Integrity Fingerprints",
              "| Doc | sha256-12 |", "|---|---|"]
    for n, p in DOCS.items():
        lines.append(f"| {n} | {sha12(p)} |")
    lines += ["", "## 6. Notes",
              f"- {sum(len(v) for v in discovered.values())} discovered "
              f"links; {len(REQUIRED_LINKS)} required; "
              f"{len(CORE_ASSETS)} core assets covered.",
              "- Regenerate after any controlled-doc change.", "",
              "## 7. Traceability",
              "All six controlled docs + ADR/CLIN/PMS/RPT/PLAYBOOK "
              "assets.", ""]
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"TLM-001 v2: discovered={sum(len(v) for v in discovered.values())} "
          f"required={len(REQUIRED_LINKS)} assets={len(CORE_ASSETS)} "
          f"all_gates=PASS")
    print("Saved -> docs/product/TLM-001_TRACEABILITY_MATRIX.md")


if __name__ == "__main__":
    main()
