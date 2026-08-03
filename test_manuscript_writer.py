"""
ProtonAI - Test Manuscript Writer
"""

import pytest
from manuscript_writer import ManuscriptWriter, SUGGESTED_REFERENCES


@pytest.fixture
def mw():
    return ManuscriptWriter(authors=["Ahmed", "Sara"])


@pytest.fixture
def res(mw):
    return mw.collect()


class TestManuscript:
    def test_imrad_sections(self, mw, res):
        md = mw.build_manuscript(res)
        for sec in ["## Abstract", "## 1. Introduction", "## 2. Methods",
                    "## 3. Results", "## 4. Discussion", "## 5. Limitations",
                    "## 6. Conclusions", "## References"]:
            assert sec in md

    def test_structured_abstract(self, mw, res):
        md = mw.build_manuscript(res)
        for k in ["**Background:**", "**Methods:**", "**Results:**", "**Conclusions:**"]:
            assert k in md

    def test_real_numbers_present(self, mw, res):
        md = mw.build_manuscript(res)
        assert f"{res['retro']['accuracy']:.3f}" in md
        assert f"{res['external']['generalization_gap']:.3f}" in md

    def test_title_and_keywords(self, mw, res):
        md = mw.build_manuscript(res)
        assert "# ProtonAI" in md
        assert "**Keywords:**" in md

    def test_references_suggested(self, mw, res):
        md = mw.build_manuscript(res)
        assert "ICRU Report 78" in md
        assert "Gamma-index" in md or "gamma" in md.lower()


class TestCoverLetter:
    def test_has_title_and_salutation(self, mw, res):
        cl = mw.build_cover_letter(res, editor="Dr. Smith", journal="Medical Physics")
        assert "Dear Dr. Smith" in cl
        assert "ProtonAI" in cl
        assert "Medical Physics" in cl

    def test_authors_or_placeholder(self, mw, res):
        assert "Ahmed" in mw.build_cover_letter(res)


class TestCollectAndSave:
    def test_collect_keys(self, mw, res):
        for k in ["clinical", "retro", "external", "improvement", "reproducibility"]:
            assert k in res

    def test_save_all(self, mw, res, tmp_path):
        mw.save_all(res, tmp_path)
        assert (tmp_path / "manuscript.md").exists()
        assert (tmp_path / "cover_letter.md").exists()


class TestReferencesConstant:
    def test_no_empty(self):
        assert all(ref.strip() for ref in SUGGESTED_REFERENCES)
