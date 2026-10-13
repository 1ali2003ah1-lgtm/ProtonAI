"""W5 TEAM: regulatory submission + publication guard (12 tests)."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REG = ROOT / "docs" / "regulatory"


def _read(n):
    return (REG / n).read_text(encoding="utf-8")


def test_intended_use():
    t = _read("INTENDED-USE-001.md")
    assert "SaMD" in t and "Class IIb" in t and "De Novo" in t


def test_risk_14971():
    t = _read("RISK-14971-001.md")
    assert "RPN" in t and "Mitigation" in t and "R-01" in t


def test_62304():
    t = _read("SOFTWARE-62304-001.md")
    assert "Class B" in t and "SOUP" in t


def test_62366():
    t = _read("USABILITY-62366-001.md").lower()
    assert "use error" in t and "summative" in t


def test_cybersecurity():
    t = _read("CYBERSECURITY-001.md")
    assert "STRIDE" in t and "threat" in t.lower()


def test_gspr_evidence():
    t = _read("GSPR-CHECKLIST-001.md")
    assert "Evidence" in t and "RISK-14971-001" in t


def test_cep_pmcf():
    t = _read("CEP-CER-001.md")
    assert "Equivalence" in t and "PMCF" in t


def test_pms_threshold():
    t = _read("PMS-001.md")
    assert "0.05" in t and "15 days" in t


def test_benefit_risk():
    t = _read("BENEFIT-RISK-001.md")
    assert "FAVOURABLE" in t and "RPN" in t


def test_ifu():
    t = _read("IFU-001.md")
    assert "Contraindications" in t and "Warnings" in t


def test_traceability_covers_risks():
    risk = _read("RISK-14971-001.md")
    trace = _read("TRACEABILITY-001.md")
    ids = set(re.findall(r"R-\d{2}", risk))
    assert ids and ids <= set(re.findall(r"R-\d{2}", trace))


def test_manuscript_complete():
    t = (ROOT / "docs" / "publication" / "PAP-3-draft.md").read_text(encoding="utf-8")
    for h in ["Ethics Statement", "Data Availability", "Conflicts of Interest",
              "Funding", "ORCID", "Limitations", "Statistical Analysis",
              "Reporting Guideline Compliance", "Protocol Registration"]:
        assert h in t
