"""C1 FINAL: ProtonAI NEXUS cockpit (Streamlit) - presentation only.

Run: pip install streamlit && streamlit run clinical_console.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import streamlit as st

from clinical_ui_core import (WINDOW_PRESETS, case_summary, compose_view,
                              triage_marker, uncertainty_heatmap, whatif_d95)

ROOT = Path(__file__).resolve().parent
SERIES = ROOT / "data" / "synth_ct" / "SYNTH-002"

st.set_page_config(page_title="ProtonAI NEXUS", layout="wide")
st.title("ProtonAI NEXUS — Clinical Cockpit")
st.caption("CLIN-002 · ADR-007 · B dose-science · PMS-001")


@st.cache_resource
def load_case():
    from dicom_reader import DicomReader
    reader = DicomReader(metadata_keys=["PatientID"])
    slices = sorted(SERIES.glob("*.dcm"))
    hu = np.stack([np.asarray(reader.read(p)["pixels"], float)
                   for p in slices])
    masks = np.load(SERIES / "ground_truth" / "masks.npy").astype(float)
    return hu, masks


hu, masks = load_case()
summ = case_summary()

with st.sidebar:
    preset = st.selectbox("Window", list(WINDOW_PRESETS))
    z = st.slider("Slice", 0, hu.shape[0] - 1, 0)
    show_gt = st.checkbox("Ground truth (green)", True)
    show_ai = st.checkbox("AI / ONNX (blue)", True)
    show_unc = st.checkbox("Uncertainty heatmap", False)
    shift = st.slider("What-if shift (rows)", 0, 10, 0)

ai_mask = None
if show_ai:
    from inference_contract import run_inference
    ai_mask = np.array(run_inference(
        hu[z], ROOT / "models" / "protonai_seg_v0.7.0.onnx")["mask"])

rgb = compose_view(hu[z], gt=masks[z] if show_gt else None, ai=ai_mask,
                   preset=preset)
if show_unc:
    conf = np.linspace(0.7, 1.0, hu.shape[1])[None, :].repeat(hu.shape[0], 0)
    rgb = (0.6 * rgb + 0.4 * uncertainty_heatmap(conf)).astype(np.uint8)

st.image(rgb, caption=f"Slice {z} · {preset}", width=420)
st.metric("What-if D95 (live)",
          f"{whatif_d95(hu[z], masks[z], np.roll(masks[z], shift, 0)):.3f}")

c1, c2, c3 = st.columns(3)
c1.metric("PMS state", summ["pms_state"].split(":")[-1].strip())
c2.metric("D95 verdict", summ["d95_verdict"])
c3.metric("Physics conf", f"{summ['kpis'].get('physics_confidence', 0):.3f}")

st.subheader("Cross-domain triage (CLIN-002)")
for r in summ["cross_rows"]:
    st.write(f"{triage_marker(r['triage'])} **{r['case']}** → {r['triage']}")

st.subheader("Dose-impact conclusion (B5)")
st.info(summ["dose_impact"])
