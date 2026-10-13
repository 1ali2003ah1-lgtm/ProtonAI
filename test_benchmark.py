"""W6 FINAL: superiority evidence + business guard (10 tests)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _res():
    return json.loads((ROOT / "benchmark_results.json").read_text(encoding="utf-8"))


def test_methods_present():
    assert {"protonai", "atlas", "commercial_sim",
            "manual_sim"} <= set(_res()["methods"])


def test_protonai_beats_atlas():
    m = _res()["methods"]
    assert m["protonai"]["dice_mean"] > m["atlas"]["dice_mean"]


def test_all_verdicts_superior():
    c = _res()["comparisons"]
    assert all(c[k]["verdict"] == "superior" for k in c)


def test_effect_sizes_large():
    c = _res()["comparisons"]
    assert all(c[k]["cliffs_delta"] > 0.5 for k in c)


def test_pooled_power():
    assert _res()["pooled_n"] == 48


def test_runtime_recorded():
    assert _res()["methods"]["protonai"]["runtime_ms"] > 0


def test_benchmark_md():
    t = (ROOT / "docs" / "business" / "BENCHMARK-001.md").read_text(encoding="utf-8")
    assert "| Method |" in t and "Cliff's delta" in t


def test_readme_evidence():
    t = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "## Evidence & Benchmarks" in t and "superior" in t


def test_licensing_pricing():
    t = (ROOT / "docs" / "business" / "LICENSING-001.md").read_text(encoding="utf-8")
    assert "Dual-license" in t and "$25,000" in t and "CLA" in t


def test_loi_ready():
    t = (ROOT / "docs" / "business" / "LOI-TEMPLATE-001.md").read_text(encoding="utf-8")
    assert "Non-Binding" in t and "Signatures" in t
