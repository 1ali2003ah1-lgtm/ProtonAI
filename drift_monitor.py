"""
ProtonAI - Monitoring: Model Drift (post-market)
مراقبة انجراف الأداء/التوزيع بعد النشر:
- DriftMonitor: z-score لمتوسط نافذة حديثة مقابل baseline ← GREEN/AMBER/RED.
- psi: مؤشر استقرار السكان (Population Stability Index).
يغلق FM-08 ويدعم المراقبة المستمرة (SaMD post-market).
"""

import math


class DriftMonitor:
    def __init__(self, baseline_mean: float, baseline_std: float,
                 amber: float = 2.0, red: float = 3.0, window: int = 20):
        if baseline_std <= 0:
            raise ValueError("baseline_std لازم تكون موجبة")
        self.bm = baseline_mean
        self.bs = baseline_std
        self.amber, self.red, self.window = amber, red, window
        self.values = []

    def update(self, value: float):
        self.values.append(value)
        self.values = self.values[-self.window:]

    def zscore(self) -> float:
        if not self.values:
            return 0.0
        m = sum(self.values) / len(self.values)
        return (m - self.bm) / self.bs

    def status(self) -> str:
        z = abs(self.zscore())
        if z >= self.red: return "RED"
        if z >= self.amber: return "AMBER"
        return "GREEN"


def psi(expected: list, actual: list, eps: float = 1e-6) -> float:
    """مؤشر استقرار السكان بين توزيعين (نسب بنفس الطول)"""
    e = [x + eps for x in expected]
    a = [x + eps for x in actual]
    return sum((ai - ei) * math.log(ai / ei) for ai, ei in zip(a, e))
