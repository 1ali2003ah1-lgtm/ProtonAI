"""B5 FINAL: dose-impact report guard (5 tests, incl. path-safety)."""
from __future__ import annotations

import json
from pathlib import Path

from make_dose_impact import OUT_JSON, OUT_MD

ROOT = Path(__file__).resolve().parent


def test_artifact_keys():
    r = json.loads(OUT_JSON.read_text(encoding="utf-8"))
    assert {"d95", "oar_v20", "tcp_delta_mean", "conclusion"} <= set(r)


def test_doc_controlled():
    t = OUT_MD.read_text(encoding="utf-8")
    assert "DOSE-IMPACT-001" in t and "EFFECTIVE" in t and "Methods" in t


def test_verdicts_valid():
    r = json.loads(OUT_JSON.read_text(encoding="utf-8"))
    assert r["d95"]["verdict"] in ("SUPERIOR", "NON_INFERIOR", "NOT_ESTABLISHED")


def test_safety_rpt_untouched():
    rpt = ROOT / "EXPERIMENT_REPORT.md"
    before = rpt.read_text(encoding="utf-8") if rpt.exists() else None
    from make_dose_impact import main
    main()
    after = rpt.read_text(encoding="utf-8") if rpt.exists() else None
    assert before == after


def test_safety_adr_set_stable():
    d = ROOT / "docs" / "quality_system" / "iso_13485"
    before = sorted(x.name for x in d.glob("ADR*"))
    from make_dose_impact import main
    main()
    after = sorted(x.name for x in d.glob("ADR*"))
    assert before == after
