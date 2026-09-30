"""P7-S2: statistical PMS guard (7 tests)."""
from __future__ import annotations

import json
from pathlib import Path

from tools.run_pms_surveillance import (DRIFT_ALPHA, DRIFT_MIN_DELTA,
                                        composite, z_drift_verdict)

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "pms_surveillance.json"
LEDGER = ROOT / "pms_ledger.json"
MD = ROOT / "docs" / "quality_system" / "iso_13485" / \
    "PMS-001_POST_MARKET_SURVEILLANCE.md"


def test_artifacts_exist():
    assert OUT.exists() and LEDGER.exists() and MD.exists()


def test_z_test_properties():
    assert z_drift_verdict([(1, 50)])[0] == "STABLE (insufficient history)"
    assert z_drift_verdict([(20, 50), (10, 50), (5, 50)])[0] == "STABLE"
    assert z_drift_verdict([(5, 50)] * 3)[0] == "STABLE"
    d, p = z_drift_verdict([(1, 50), (1, 50), (20, 50)])
    assert d.startswith("DRIFT") and p is not None and p < DRIFT_ALPHA


def test_composite_logic():
    assert composite("STABLE", 0, "PASS")[0] == "SURVEILLANCE: STABLE"
    assert composite("DRIFT: x", 0, "PASS")[0] == "SURVEILLANCE: ESCALATE"
    assert composite("STABLE", 2, "PASS")[0] == "SURVEILLANCE: ESCALATE"
    assert composite("STABLE", 0, "FAIL")[0] == "SURVEILLANCE: ESCALATE"


def test_artifact_consistency():
    a = json.loads(OUT.read_text(encoding="utf-8"))
    counts = [tuple(c) for c in a["counts"]]
    assert a["drift_verdict"] == z_drift_verdict(counts)[0]
    assert a["state"] == composite(a["drift_verdict"], a["urgent_count"],
                                   a["io_verdict"])[0]


def test_ledger_appended():
    a = json.loads(OUT.read_text(encoding="utf-8"))
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    assert ledger and ledger[-1]["generated"] == a["generated"]


def test_md_statistical_rule():
    t = MD.read_text(encoding="utf-8")
    for s in ("0.05", "0.10", "z-test", "Quarterly", "CAPA", "24h"):
        assert s in t


def test_traceability():
    t = MD.read_text(encoding="utf-8")
    for ref in ("CLIN-001", "CLIN-002", "DATA-ACQ-001", "ISO 20416"):
        assert ref in t
