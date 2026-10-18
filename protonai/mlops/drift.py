"""Model drift detection (input + prediction drift).
Designed & developed by: Ali Hussein Thajil

Methods:
- Population Stability Index (PSI)
- Kolmogorov-Smirnov (KS) test
- Simple statistical drift score
"""
from __future__ import annotations
import json, time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np


@dataclass
class DriftReport:
    timestamp: float = field(default_factory=time.time)
    psi: float = 0.0
    ks_stat: float = 0.0
    mean_shift: float = 0.0
    std_ratio: float = 1.0
    drift_detected: bool = False
    severity: str = "none"
    samples: int = 0


class DriftMonitor:
    def __init__(self, state_path: str = "data/drift.json"):
        self.state_path = Path(state_path)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.history: List[Dict] = []
        self.baseline: Optional[np.ndarray] = None
        self._load()

    def set_baseline(self, values: np.ndarray):
        self.baseline = np.asarray(values).flatten()
        self._save()

    def _psi(self, reference: np.ndarray, current: np.ndarray,
             bins: int = 10) -> float:
        breakpoints = np.linspace(
            min(reference.min(), current.min()),
            max(reference.max(), current.max()), bins + 1)
        ref_hist = np.histogram(reference, bins=breakpoints)[0] / len(reference)
        cur_hist = np.histogram(current, bins=breakpoints)[0] / len(current)
        ref_hist = np.clip(ref_hist, 1e-6, None)
        cur_hist = np.clip(cur_hist, 1e-6, None)
        return float(np.sum((cur_hist - ref_hist) * np.log(cur_hist / ref_hist)))

    def _ks(self, reference: np.ndarray, current: np.ndarray) -> float:
        r = np.sort(reference); c = np.sort(current)
        all_v = np.concatenate([r, c])
        cdf_r = np.searchsorted(r, all_v, side="right") / len(r)
        cdf_c = np.searchsorted(c, all_v, side="right") / len(c)
        return float(np.max(np.abs(cdf_r - cdf_c)))

    def check(self, values: np.ndarray) -> DriftReport:
        values = np.asarray(values).flatten()
        report = DriftReport(samples=len(values))
        if self.baseline is None or len(self.baseline) == 0:
            self.baseline = values
            self._save()
            return report
        psi = self._psi(self.baseline, values)
        ks = self._ks(self.baseline, values)
        mean_shift = float(values.mean() - self.baseline.mean())
        std_ratio = float(values.std() / max(self.baseline.std(), 1e-9))
        drift_score = psi + ks + abs(mean_shift) / max(abs(self.baseline.mean()), 1e-9)
        report.psi = psi
        report.ks_stat = ks
        report.mean_shift = mean_shift
        report.std_ratio = std_ratio
        if psi > 0.25 or ks > 0.3:
            report.severity = "high"
            report.drift_detected = True
        elif psi > 0.1 or ks > 0.15:
            report.severity = "medium"
            report.drift_detected = True
        else:
            report.severity = "low" if drift_score > 0.05 else "none"
        self.history.append({"timestamp": report.timestamp, "psi": psi,
                             "ks": ks, "severity": report.severity})
        self._save()
        return report

    def trend(self, window: int = 30) -> List[Dict]:
        return self.history[-window:]

    def _load(self):
        if self.state_path.exists():
            try:
                data = json.loads(self.state_path.read_text())
                self.history = data.get("history", [])
                bl = data.get("baseline")
                self.baseline = np.array(bl) if bl else None
            except Exception:
                pass

    def _save(self):
        self.state_path.write_text(json.dumps({
            "history": self.history,
            "baseline": self.baseline.tolist() if self.baseline is not None else None,
        }))
