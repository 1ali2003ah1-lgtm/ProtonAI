"""C1 FINAL: NEXUS cockpit core guard (7 tests, no Streamlit)."""
from __future__ import annotations

import numpy as np

from clinical_ui_core import (WINDOW_PRESETS, case_summary, compose_view,
                              normalize_display, overlay_rgb, triage_marker,
                              uncertainty_heatmap, whatif_d95)


def test_all_presets_bounds():
    for p in WINDOW_PRESETS:
        g = normalize_display(np.array([-2000, 0, 3000]), p)
        assert g.dtype == np.uint8 and 0 <= g.min() and g.max() <= 255


def test_overlay_only_where_mask():
    rgb = np.zeros((4, 4, 3), dtype=np.uint8)
    m = np.zeros((4, 4)); m[1, 1] = 1
    out = overlay_rgb(rgb, m, (255, 0, 0))
    assert out[0, 0].tolist() == [0, 0, 0] and out[1, 1, 0] > 0


def test_compose_view_adds_gt():
    hu = np.zeros((6, 6)); m = np.zeros((6, 6)); m[2, 2] = 1
    base = compose_view(hu)
    with_gt = compose_view(hu, gt=m)
    assert with_gt[2, 2, 1] > base[2, 2, 1]


def test_uncertainty_direction():
    hm = uncertainty_heatmap(np.array([0.0, 1.0]))
    assert hm[0, 0] > hm[0, 1] and hm[1, 1] > hm[1, 0]


def test_summary_keys_robust():
    assert {"kpis", "pms_state", "model_card", "dose_impact",
            "d95_verdict"} <= set(case_summary())


def test_markers():
    assert triage_marker("URGENT") == "🔴" and triage_marker("x") == "⚪"


def test_whatif_2d_sensitivity():
    ct = np.zeros((60, 40)); m = np.zeros((60, 40)); m[25:35, 10:30] = 1
    good = whatif_d95(ct, m, m)
    bad = whatif_d95(ct, m, np.roll(m, 6, axis=0))
    assert good > 0.9 and good - bad > 0.2
