"""MLOps layer tests."""
import os, sys, tempfile
import numpy as np
sys.path.insert(0, os.getcwd())

from protonai.mlops.registry import ModelRegistry
from protonai.mlops.drift import DriftMonitor


def test_registry_register_promote():
    with tempfile.TemporaryDirectory() as td:
        r = ModelRegistry(root=os.path.join(td, "reg"))
        v1 = r.register("v1.0.0", metrics={"dice": 0.95})
        assert v1.version == "v1.0.0"
        r.promote("v1.0.0", "production")
        assert r.current("production").version == "v1.0.0"


def test_registry_rollback():
    with tempfile.TemporaryDirectory() as td:
        r = ModelRegistry(root=os.path.join(td, "reg"))
        r.register("v1", metrics={"dice": 0.95})
        r.register("v2", metrics={"dice": 0.96})
        r.promote("v2", "production")
        r.rollback("production", "v1")
        assert r.current("production").version == "v1"


def test_drift_no_drift_on_same_distribution():
    with tempfile.TemporaryDirectory() as td:
        m = DriftMonitor(state_path=os.path.join(td, "d.json"))
        rng = np.random.default_rng(0)
        baseline = rng.normal(0, 1, 1000)
        m.set_baseline(baseline)
        rep = m.check(rng.normal(0, 1, 500))
        assert rep.severity in ("none", "low")


def test_drift_detected_on_shift():
    with tempfile.TemporaryDirectory() as td:
        m = DriftMonitor(state_path=os.path.join(td, "d.json"))
        rng = np.random.default_rng(1)
        m.set_baseline(rng.normal(0, 1, 1000))
        rep = m.check(rng.normal(5, 1, 500))
        assert rep.drift_detected and rep.severity == "high"
