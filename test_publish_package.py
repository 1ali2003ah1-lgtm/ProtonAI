"""H2 FINAL: publish guard (8 tests)."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SITE = ROOT / "docs" / "site" / "index.html"
WF = ROOT / ".github" / "workflows" / "pages.yml"
CFF = ROOT / "CITATION.cff"
ZEN = ROOT / ".zenodo.json"
GUIDE = ROOT / "docs" / "publication" / "PUBLISH-GUIDE-001.md"
NOTES = ROOT / "docs" / "publication" / "RELEASE-NOTES-v0.9.0.md"


def test_site_meta_cite():
    t = SITE.read_text(encoding="utf-8")
    assert "og:title" in t and "Cite" in t


def test_site_i18n():
    assert "data-en" in SITE.read_text(encoding="utf-8")


def test_workflow_pages():
    t = WF.read_text(encoding="utf-8")
    assert "github-pages" in t and "docs/site" in t


def test_citation():
    assert "cff-version" in CFF.read_text(encoding="utf-8")


def test_zenodo_valid():
    assert {"title", "upload_type", "creators", "license"} <= set(
        json.loads(ZEN.read_text(encoding="utf-8")))


def test_guide_steps():
    t = GUIDE.read_text(encoding="utf-8")
    assert "gh api" in t and "Zenodo" in t and "DOI" in t


def test_release_notes():
    t = NOTES.read_text(encoding="utf-8")
    assert "v0.9.0" in t and "NOT for clinical use" in t


def test_safety_rpt_exists():
    assert (ROOT / "EXPERIMENT_REPORT.md").exists()
