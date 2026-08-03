"""
ProtonAI - Test Paper Builder
"""

import pytest
from paper_builder import PaperBuilder


MIN = {
    "clinical": {"state": "delivered", "overall": "GREEN",
                 "indicators": [("Gamma", "🟢"), ("المدى", "🟢")]},
    "retro": {"accuracy": 0.85, "sensitivity": 0.8, "specificity": 0.9,
              "ppv": 0.8, "npv": 0.9},
    "external": {"internal_accuracy": 0.9, "external_accuracy": 0.88,
                 "generalization_gap": 0.02, "verdict": "robust",
                 "publication_ready": True},
    "improvement": {"n_issues": 1},
    "reproducibility": {"seeds": [42], "python": "3.10"},
}


@pytest.fixture
def pb():
    return PaperBuilder()


class TestBuild:
    def test_all_sections(self, pb):
        md = pb.build(MIN)
        for sec in ["## الملخص", "## 1. المقدمة", "## 2. المنهج", "## 3. النتائج",
                    "## 4. النقاش", "## 5. القيود", "## 6. قابلية التكرار",
                    "## 7. الخاتمة"]:
            assert sec in md

    def test_title_and_keywords(self, pb):
        md = pb.build(MIN)
        assert "# ProtonAI" in md
        assert "الكلمات المفتاحية" in md

    def test_results_values(self, pb):
        md = pb.build(MIN)
        assert "0.850" in md      # الدقة الاستعادية
        assert "0.020" in md      # فارق التعميم
        assert "robust" in md

    def test_indicators_table(self, pb):
        md = pb.build(MIN)
        assert "| Gamma | 🟢 |" in md

    def test_limitations_honest(self, pb):
        md = pb.build(MIN)
        assert "Monte Carlo" in md
        assert "استعادي" in md

    def test_reproducibility(self, pb):
        md = pb.build(MIN)
        assert "[42]" in md
        assert "3.10" in md

    def test_authors(self):
        md = PaperBuilder(authors=["أحمد", "سارة"]).build(MIN)
        assert "أحمد" in md and "سارة" in md


class TestCollect:
    def test_collect_keys(self, pb):
        r = pb.collect()
        for k in ["clinical", "retro", "external", "improvement", "reproducibility"]:
            assert k in r

    def test_collect_and_build(self, pb):
        md = pb.build(pb.collect())
        assert "## الملخص" in md


class TestStats:
    def test_stats_positive(self, pb):
        md = pb.build(MIN)
        s = pb.stats(md)
        assert s["sections"] >= 8
        assert s["abstract_words"] > 0
        assert s["chars"] > 0


class TestSave:
    def test_saves(self, pb, tmp_path):
        md = pb.build(MIN)
        p = pb.save(md, tmp_path / "paper.md")
        assert p.exists()
        assert "## الملخص" in p.read_text(encoding="utf-8")
