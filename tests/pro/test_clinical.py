"""Clinical intelligence tests."""
import os, sys, tempfile
import numpy as np
sys.path.insert(0, os.getcwd())

from protonai.clinical.cbir import CaseRetrieval
from protonai.clinical.optimizer import ProtonOptimizer
from protonai.clinical.rules import ClinicalRuleEngine


def test_cbir_finds_similar_case():
    with tempfile.TemporaryDirectory() as td:
        c = CaseRetrieval(index_path=os.path.join(td, "i.pkl"),
                          metadata_path=os.path.join(td, "m.json"))
        rng = np.random.default_rng(0)
        base_img = rng.normal(100, 20, (64, 64))
        c.add_case("CASE-A", base_img)
        c.add_case("CASE-B", rng.normal(-500, 50, (64, 64)))
        c.add_case("CASE-SIMILAR", base_img + rng.normal(0, 5, (64, 64)))
        results = c.search(base_img, top_k=2)
        assert results[0][0] in ("CASE-A", "CASE-SIMILAR")


def test_optimizer_improves_target_coverage():
    opt = ProtonOptimizer(prescription_gy=70.0)
    target = np.zeros(1000, dtype=bool)
    target[400:600] = True
    r = opt.optimize(n_spots=50, n_voxels=1000, target_mask=target,
                     max_iter=100)
    assert r.target_d95 > 0
    assert len(r.spot_weights) == 50


def test_rules_trigger_on_low_v95():
    engine = ClinicalRuleEngine()
    alerts = engine.evaluate({"physics": {"v95": 0.85, "tcp": 0.95,
                                          "hi": 0.1, "ci": 1.0},
                              "robust_worst_d95": 0.95,
                              "uncertainty_mean": 0.05})
    ids = [a.rule_id for a in alerts]
    assert "RULE-D95-LOW" in ids
    assert any(a.severity == "critical" for a in alerts)


def test_rules_no_alert_on_good_plan():
    engine = ClinicalRuleEngine()
    alerts = engine.evaluate({"physics": {"v95": 0.98, "tcp": 0.95,
                                          "hi": 0.1, "ci": 1.0},
                              "robust_worst_d95": 0.95,
                              "uncertainty_mean": 0.05})
    critical = [a for a in alerts if a.severity == "critical"]
    assert not critical
