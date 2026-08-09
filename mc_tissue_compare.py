"""
ProtonAI - Physics: Monte Carlo على أنسجة غير متجانسة
- مدى تحليلي (CSDA) لكل نسيج عبر RSP.
- مدى Monte Carlo مبثر (straggling) ومقارنته بالتحليلي.
- حساب WEPL لطبقات غير متجانسة (عظم/رئة/نسيج رخو).
"""

import numpy as np

TISSUES = {
    "water":  {"rsp": 1.00},
    "muscle": {"rsp": 1.05},
    "lung":   {"rsp": 0.30},
    "bone":   {"rsp": 1.75},
}

STRAGGLE = 0.012  # 1.2% straggling نسبي


def csda_range_cm(energy: float) -> float:
    """مدى CSDA تقريبي بالماء (سم) لطاقة MeV"""
    return 0.0022 * (energy ** 1.77)


def analytic_range(energy: float, tissue: str) -> float:
    """المدى التحليلي بنسيج محدد = مدى الماء / RSP"""
    return csda_range_cm(energy) / TISSUES[tissue]["rsp"]


def mc_range(energy: float, tissue: str, n: int = 5000, seed: int = 0) -> float:
    """مدى Monte Carlo: متوسط عينات مدى مبثرة حول المدى التحليلي"""
    rng = np.random.default_rng(seed)
    R = analytic_range(energy, tissue)
    samples = rng.normal(R, STRAGGLE * R, n)
    return float(np.mean(samples))


def compare(energy: float, tissue: str, seed: int = 0) -> dict:
    """مقارنة المدى التحليلي مقابل Monte Carlo"""
    a = analytic_range(energy, tissue)
    m = mc_range(energy, tissue, seed=seed)
    return {"tissue": tissue, "analytic": a, "mc": m,
            "rel_diff": abs(m - a) / a}


def wepl(layers) -> float:
    """
    Water-Equivalent Path Length لطبقات غير متجانسة.
    layers: قائمة من (سماكة_سم, نسيج)
    """
    return float(sum(th * TISSUES[t]["rsp"] for th, t in layers))


def residual_range(energy: float, layers) -> float:
    """المدى المتبقي بالماء بعد عبور الطبقات (سالب = لا يصل)"""
    return csda_range_cm(energy) - wepl(layers)
