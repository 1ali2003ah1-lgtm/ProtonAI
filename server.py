"""C2 FINAL: NEXUS Enterprise API + world-class React SPA.

Endpoints: health, summary, presets, dose-impact, whatif, dvh(aligned),
slice, tcp-ntcp, partnership. Serves web/index.html (React CDN, i18n
EN/AR + RTL, glassmorphism, canvas viewer, live DVH).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from fastapi import FastAPI
from fastapi.responses import FileResponse

from clinical_ui_core import (WINDOW_PRESETS, case_summary, normalize_display,
                              whatif_d95)
from dose_bridge import compute_dose
from dose_bridge import dvh as calc_dvh

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
PART = ROOT / "docs" / "partnership"
app = FastAPI(title="ProtonAI NEXUS API", version="2.0")

_VOL = _GT = _AI = None


def _synth():
    global _VOL, _GT, _AI
    if _VOL is None:
        _VOL, _GT, _AI = [], [], []
        for z in range(8):
            c = np.zeros((60, 40)); t = np.zeros((60, 40))
            r0 = 25 + z
            t[r0:r0 + 8, 12:28] = 1
            c += np.linspace(-200, 200, 60)[:, None] * 0.1
            _VOL.append(c); _GT.append(t); _AI.append(np.roll(t, 1, 0))
    return _VOL, _GT, _AI


@app.get("/health")
def health():
    return {"status": "ok", "service": "ProtonAI NEXUS API"}


@app.get("/api/summary")
def summary():
    return case_summary()


@app.get("/api/presets")
def presets():
    return WINDOW_PRESETS


@app.get("/api/dose-impact")
def dose_impact():
    p = ROOT / "dose_impact_report.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


@app.get("/api/tcp-ntcp")
def tcp_ntcp():
    p = ROOT / "tcp_ntcp_results.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


@app.get("/api/partnership")
def partnership():
    return sorted(x.name for x in PART.glob("*.md")) if PART.exists() else []


@app.post("/api/whatif")
def whatif(payload: dict):
    shift = int(payload.get("shift", 0))
    ct = np.zeros((60, 40)); m = np.zeros((60, 40)); m[25:35, 10:30] = 1
    return {"shift": shift, "d95": whatif_d95(ct, m, np.roll(m, shift, 0))}


@app.get("/api/dvh")
def dvh(shift: int = 0):
    ct = np.zeros((60, 40)); m = np.zeros((60, 40)); m[25:35, 10:30] = 1
    bins, cum = calc_dvh(compute_dose(ct, m), np.roll(m, shift, 0))
    return {"bins": bins[:-1].tolist(), "cum": cum.tolist()}


@app.get("/api/segment")
def segment(z: int = 0):
    from tools import train_seg
    import numpy as _np
    model = train_seg.ensure_model()
    img, gt = train_seg.make_sample(_np.random.default_rng(1000 + z))
    pred, unc = train_seg.predict_unc(model, img)
    h = train_seg.hd95(pred, gt)
    return {"dice": train_seg.dice(pred, gt),
            "hd95": (0.0 if h != h else h),
            "uncertainty": float(unc.mean())}


@app.get("/api/slice")
def slice_(z: int = 0):
    vol, gt, ai = _synth()
    z = max(0, min(z, len(vol) - 1))
    return {"gray": normalize_display(vol[z]).tolist(),
            "gt": gt[z].tolist(), "ai": ai[z].tolist()}


@app.get("/")
def index():
    return FileResponse(WEB / "index.html")
