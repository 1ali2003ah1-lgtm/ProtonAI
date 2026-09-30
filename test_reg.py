"""A6 enhanced: regulatory strategy guard (7 tests)."""
from __future__ import annotations

from tools.make_reg import (CYBER, FDA_STEPS, GAPS, GSPR, OUT, PMCF,
                            PREDICATES, UDI)


def test_doc_exists_controlled():
    t = OUT.read_text(encoding="utf-8")
    assert "REG-001" in t and "| 2.0 |" in t and "EFFECTIVE" in t


def test_predicate_analysis():
    t = OUT.read_text(encoding="utf-8")
    for p in PREDICATES:
        assert p["device"] in t and p["manufacturer"] in t
        assert "substantial equivalence" in t


def test_gspr_table():
    t = OUT.read_text(encoding="utf-8")
    for g in GSPR:
        assert g["req"] in t and g["asset"] in t


def test_udi_path():
    t = OUT.read_text(encoding="utf-8")
    for item in ("UDI-DI", "EUDAMED", "GUDID"):
        assert item in t


def test_cybersecurity_file():
    t = OUT.read_text(encoding="utf-8")
    assert "SBOM" in t and "vulnerability" in t.lower()
    for item in CYBER:
        assert item.split("(")[0].strip()[:20] in t


def test_pmcf_plan():
    t = OUT.read_text(encoding="utf-8")
    assert "PMCF" in t and "PMS-001" in t


def test_honest_gaps_and_traceability():
    t = OUT.read_text(encoding="utf-8")
    for g in GAPS:
        assert g in t
    for ref in ("PRM-001", "USP-001", "IEC 62304", "MDR 2017/745",
                "21 CFR", "FDA Cybersecurity Guidance 2023"):
        assert ref in t
