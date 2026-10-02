"""C1 FINAL: pure, testable NEXUS cockpit logic (numpy-only).

Window presets, compose_view (normalize+overlays), uncertainty heatmap,
unified robust case summary, and correct 2D what-if D95 (B1).
Presentation (Streamlit) in clinical_console.py is untested.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent

WINDOW_PRESETS = {
    "mediastinum": (-200.0, 300.0),
    "lung": (-1200.0, 200.0),
    "bone": (-400.0, 1800.0),
    "brain": (0.0, 80.0),
}
TRIAGE_EMOJI = {"AUTO": "🟢", "REVIEW": "🟡", "URGENT": "🔴"}


def triage_marker(t):
    return TRIAGE_EMOJI.get(t, "⚪")


def normalize_display(hu, preset="mediastinum"):
    lo, hi = WINDOW_PRESETS[preset]
    x = np.clip(np.asarray(hu, float), lo, hi)
    return (((x - lo) / (hi - lo)) * 255).astype(np.uint8)


def overlay_rgb(rgb, mask, color, alpha=0.5):
    out = rgb.astype(float).copy()
    m = np.asarray(mask) > 0
    for i, c in enumerate(color):
        out[..., i][m] = (1 - alpha) * out[..., i][m] + alpha * c
    return out.astype(np.uint8)


def compose_view(hu, gt=None, ai=None, preset="mediastinum", alpha=0.5):
    rgb = np.stack([normalize_display(hu, preset)] * 3, axis=-1)
    if gt is not None:
        rgb = overlay_rgb(rgb, gt, (0, 220, 90), alpha)
    if ai is not None:
        rgb = overlay_rgb(rgb, ai, (60, 140, 255), alpha)
    return rgb


def uncertainty_heatmap(conf):
    c = np.clip(np.asarray(conf, float), 0, 1)
    return np.stack([255 * (1 - c), 255 * c, np.zeros_like(c)],
                    axis=-1).astype(np.uint8)


def _load(name, default):
    p = ROOT / name
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default


def case_summary():
    dash = _load("clinical_dashboard.json", {})
    pms = _load("pms_surveillance.json", {})
    card = _load("models/MODEL_CARD.json", {})
    impact = _load("dose_impact_report.json", {})
    return {"kpis": dash.get("kpis", {}),
            "cross_rows": dash.get("scopes", {}).get("cross_domain", {})
            .get("rows", []),
            "pms_state": pms.get("state", "UNKNOWN"),
            "model_card": card,
            "dose_impact": impact.get("conclusion", "pending"),
            "d95_verdict": impact.get("d95", {}).get("verdict", "pending")}


def whatif_d95(ct2d, plan_mask, eval_mask):
    """Plan on plan_mask; evaluate on eval_mask (hypothesized truth)."""
    from dose_bridge import compute_dose, dvh_metrics
    return dvh_metrics(compute_dose(ct2d, plan_mask), eval_mask)["D95"]
