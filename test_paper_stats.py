"""
ProtonAI - Test Paper Statistics
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "docs"))
from paper_stats import summary


class TestStats:
    def test_positive(self):
        s = summary()
        assert s["units"] > 0
        assert s["tests"] > 0
        assert s["sites"] > 0
        assert s["top_risk_rpn"] > 0

    def test_risk_exists(self):
        s = summary()
        assert s["top_risk_id"].startswith("FM-")
