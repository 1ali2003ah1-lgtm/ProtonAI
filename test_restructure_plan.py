"""
ProtonAI - Test Restructure Plan (dry-run validation بالـ CI)
يتحقق من صحة خطة النقل بدون تحريك أي ملف.
"""

from pathlib import Path
from restructure_for_laptop import MAPPING, PACKAGES, REWRITES


class TestPlan:
    def test_sources_exist(self):
        for old in MAPPING:
            assert Path(old).exists(), f"مصدر مفقود: {old}"

    def test_dests_unique(self):
        dests = list(MAPPING.values())
        assert len(dests) == len(set(dests))

    def test_packages_allowed(self):
        for d in MAPPING.values():
            assert d.split("/")[0] in PACKAGES

    def test_rewrites_cover_mapping(self):
        names = {old.replace(".py", "") for old in MAPPING}
        for old, _ in REWRITES:
            base = old.split()[1]
            assert base in names or base in {"api_main"}
