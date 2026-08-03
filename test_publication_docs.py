"""
ProtonAI - Test Publication Docs
اختبارات مولّد التوثيق (تحليل ساكن + استبعاد اختبارات + markdown)
"""

import pytest
from publication_docs import DocumentationGenerator, _first_line

SAMPLE = '''
"""موديول تجريبي."""

class Foo:
    """كلاس فو."""
    def method(self):
        pass

def bar():
    """دالة بار."""
    return 1
'''


@pytest.fixture
def gen(tmp_path):
    (tmp_path / "sample.py").write_text(SAMPLE, encoding="utf-8")
    (tmp_path / "test_skip.py").write_text("class X: pass", encoding="utf-8")
    (tmp_path / "_private.py").write_text("class Y: pass", encoding="utf-8")
    return DocumentationGenerator(root=tmp_path)


class TestFirstLine:
    def test_multiline(self):
        assert _first_line("سطر أول\nسطر ثاني") == "سطر أول"

    def test_none(self):
        assert _first_line(None) == ""


class TestScan:
    def test_excludes_test_and_private(self, gen):
        names = [m["module"] for m in gen.scan()]
        assert "sample" in names
        assert "test_skip" not in names
        assert "_private" not in names

    def test_extracts_class_and_doc(self, gen):
        foo = next(m for m in gen.scan() if m["module"] == "sample")
        assert foo["classes"][0]["name"] == "Foo"
        assert foo["classes"][0]["doc"] == "كلاس فو."

    def test_extracts_function_and_doc(self, gen):
        foo = next(m for m in gen.scan() if m["module"] == "sample")
        assert foo["functions"][0]["name"] == "bar"
        assert foo["functions"][0]["doc"] == "دالة بار."

    def test_method_not_top_level_function(self, gen):
        foo = next(m for m in gen.scan() if m["module"] == "sample")
        fn_names = [f["name"] for f in foo["functions"]]
        assert "method" not in fn_names  # method داخل class، مو علوية

    def test_include_filter(self, tmp_path):
        (tmp_path / "a.py").write_text("class A: pass", encoding="utf-8")
        (tmp_path / "b.py").write_text("class B: pass", encoding="utf-8")
        g = DocumentationGenerator(root=tmp_path, include=["a"])
        names = [m["module"] for m in g.scan()]
        assert names == ["a"]

    def test_empty_dir(self, tmp_path):
        g = DocumentationGenerator(root=tmp_path)
        assert g.scan() == []


class TestMarkdown:
    def test_header_and_count(self, gen):
        md = gen.to_markdown()
        assert "توثيق جاهز للنشر" in md
        assert "**عدد الوحدات:** 1" in md

    def test_module_and_members(self, gen):
        md = gen.to_markdown()
        assert "### `sample`" in md
        assert "class `Foo`" in md
        assert "def `bar`" in md
        assert "كلاس فو." in md

    def test_empty_dir_valid(self, tmp_path):
        g = DocumentationGenerator(root=tmp_path)
        assert "لا توجد وحدات" in g.to_markdown()
