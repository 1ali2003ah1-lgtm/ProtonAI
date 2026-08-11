"""
ProtonAI - Config Loader
تحميل إعداد مركزي (config.yaml) مع قيم افتراضية آمنة.
- لا hardcoded: الوحدات تقرأ من هنا.
- محمي بـ yaml: يشتغل بالـ CI حتى لو ما توفر yaml (يرجع الافتراضيات).
"""

import copy
from pathlib import Path

try:
    import yaml
    YAML_AVAILABLE = True
except Exception:  # pragma: no cover
    yaml = None
    YAML_AVAILABLE = False

DEFAULTS = {
    "physics": {"straggle": 0.012, "gamma_dd": 0.02, "gamma_dt": 2.0},
    "ai": {"dice_target": 0.85, "ece_target": 0.05},
    "safety": {"amber_threshold": 0.02, "red_threshold": 0.05},
    "data": {"hu_min": -1000.0, "hu_max": 1000.0},
}


def load_config(path=None) -> dict:
    """تحميل الإعداد ودمجه فوق الافتراضيات"""
    cfg = copy.deepcopy(DEFAULTS)
    if path and YAML_AVAILABLE and Path(path).exists():
        with open(path, encoding="utf-8") as f:
            loaded = yaml.safe_load(f) or {}
        for k, v in loaded.items():
            if isinstance(v, dict) and isinstance(cfg.get(k), dict):
                cfg[k].update(v)
            else:
                cfg[k] = v
    return cfg


def get(cfg: dict, *keys, default=None):
    """قراءة متداخلة آمنة: get(cfg,"ai","ece_target")"""
    cur = cfg
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur
