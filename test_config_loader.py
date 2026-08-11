"""
ProtonAI - Test Config Loader
"""

from config_loader import load_config, get, DEFAULTS


class TestDefaults:
    def test_loads_defaults(self):
        cfg = load_config()
        assert cfg["ai"]["ece_target"] == 0.05
        assert cfg["ai"]["dice_target"] == 0.85

    def test_physics(self):
        cfg = load_config()
        assert cfg["physics"]["straggle"] == 0.012


class TestGet:
    def test_nested(self):
        cfg = load_config()
        assert get(cfg, "safety", "red_threshold") == 0.05

    def test_missing_returns_default(self):
        cfg = load_config()
        assert get(cfg, "nope", "nothing", default=7) == 7

    def test_no_mutation(self):
        a = load_config()
        a["ai"]["ece_target"] = 1.0
        assert DEFAULTS["ai"]["ece_target"] == 0.05
