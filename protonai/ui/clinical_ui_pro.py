"""ProtonAI PRO Console v1.0.0-pro.

Designed & developed by: Ali Hussein Thajil
DOI: 10.5281/zenodo.23147530

Eight integrated tabs:
Analysis+XAI / Optimizer / 3D / CBIR / GraphQL / Audit / Registry / Webhooks
"""
from __future__ import annotations

import hashlib
import io
import json
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import make_report, pipeline, rt_export, train_seg
from protonai.clinical.cbir import CaseRetrieval
from protonai.clinical.optimizer import ProtonOptimizer
from protonai.clinical.rules import ClinicalRuleEngine
from protonai.enterprise.audit_log import AuditLog
from protonai.mlops.drift import DriftMonitor
from protonai.mlops.registry import ModelRegistry
from protonai.api.webhooks import WebhookManager
from protonai.ui import cbir_panel, design_system, xai_panel

try:
    import plotly.graph_objects as go
except Exception:
    go = None

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DEVELOPER = "Ali Hussein Thajil"
VERSION = "1.0.0-pro"
DOI = "10.5281/zenodo.23147530"

st.set_page_config(page_title="ProtonAI PRO", page_icon="🏥", layout="wide")
st.markdown("<style>" + design_system.get_all_styles() + "</style>",
            unsafe_allow_html=True)

DEFAULTS = {"cases": [], "current": None, "image": None, "chain": []}
for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


@st.cache_resource
def services():
    return {
        "cbir": CaseRetrieval(),
        "drift": DriftMonitor(),
        "registry": ModelRegistry(),
        "webhooks": WebhookManager(),
        "audit": AuditLog(),
    }


def signed(fig):
    fig.text(0.99, 0.01, "(c) Ali Hussein Thajil - ProtonAI PRO",
             ha="right", fontsize=7, color="#777", style="italic")
    return fig


def ct_figure(image, mask):
    fig, ax = plt.subplots(1, 2, figsize=(9, 4.5))
    ax[0].imshow(image, cmap="gray")
    ax[0].set_title("CT", color="#0D47A1")
    ax[1].imshow(image, cmap="gray")
    if np.asarray(mask).any():
        ax[1].contour(mask, colors="#FF1744", linewidths=1.4)
    ax[1].set_title("AI contour", color="#0D47A1")
    for axis in ax:
        axis.axis("off")
    fig.tight_layout()
    return signed(fig)


def alert_rows(alerts):
    return [{"Rule": a.rule_id, "Severity": a.severity.upper(),
             "Finding": a.message, "Recommendation": a.recommendation}
            for a in alerts]


# ── Header ────────────────────────────────────────────────
st.markdown('<div class="hero"><h1>ProtonAI PRO Console</h1>'
            '<p>Segmentation · Dose · XAI · CBIR · Audit</p>'
            '<div class="signature">Designed &amp; developed by <b>'
            + DEVELOPER + '</b></div></div>', unsafe_allow_html=True)
st.caption(f"v{VERSION} · DOI {DOI}")
st.warning("Decision-support only. Physician review and approval required.")

with st.sidebar:
    st.header("Console")
    st.session_state["nz"] = st.slider("Z-slices", 8, 32, 16)
    st.divider()
    st.metric("Analysed cases", len(st.session_state.cases))
    st.metric("CBIR database", services()["cbir"].count())
    st.divider()
    st.caption(DEVELOPER)
    st.caption(DOI)

tabs = st.tabs(["Analysis", "Optimizer", "3D", "Similar",
                "GraphQL", "Audit", "Registry", "Webhooks"])

# ── Tab 1: Analysis ───────────────────────────────────────
with tabs[0]:
    st.subheader("Clinical analysis with explainability")
    source = st.radio("Source", ["Demo", "Upload .npy"], horizontal=True)
    image = None

    if source == "Demo":
        if st.button("Run demo analysis", type="primary"):
            sample, _ = train_seg.make_sample(np.random.default_rng(42))
            image = sample[None]
    else:
        up = st.file_uploader("CT volume (.npy)", type=["npy"])
        if up is not None:
            try:
                image = np.load(io.BytesIO(up.read()))
            except Exception as exc:
                st.error(f"Load failed: {exc}")

    if image is not None:
        with st.spinner("Running pipeline..."):
            try:
                result = pipeline.run_pipeline(
                    image, {"PatientName": "DEMO"},
                    nz=st.session_state["nz"],
                    case_id=f"AHT-PRO-{int(time.time())}")
            except Exception as exc:
                st.error(f"Pipeline failed: {exc}")
                result = None

        if result is not None:
            st.session_state["current"] = result
            st.session_state["image"] = image
            summary = result["summary"]
            physics = summary["physics"]
            rep = result["rep_slice"]
            mask = result["masks"][rep]

            c = st.columns(4)
            c[0].metric("V95", f"{physics['v95']:.3f}")
            c[1].metric("TCP", f"{physics['tcp']:.3f}")
            c[2].metric("Robust D95", f"{summary['robust_worst_d95']:.3f}")
            c[3].metric("Uncertainty", f"{summary['uncertainty_mean']:.4f}")

            st.pyplot(ct_figure(image[rep], mask))

            cam = xai_panel.compute_grad_cam_simple(image[rep], mask)
            xfig = xai_panel.build_xai_visualization(
                image[rep], mask,
                uncertainty_map=result["uncertainty"][rep], grad_cam=cam)
            if xfig is not None:
                st.pyplot(xfig)

            xr = xai_panel.generate_xai_report(
                image[rep], mask, result["uncertainty"][rep], cam)
            st.progress(float(np.clip(xr["confidence_score"], 0.0, 1.0)))
            st.caption(f"Model confidence: {xr['confidence_score']:.3f}")

            alerts = ClinicalRuleEngine().evaluate(summary)
            if alerts:
                st.subheader("Clinical alerts")
                st.dataframe(alert_rows(alerts), use_container_width=True)
            else:
                st.success("No clinical alerts — plan quality acceptable.")

            services()["cbir"].add_case(summary["case_id"], image[rep],
                                        mask, {"physics": physics})
            services()["audit"].record("case.completed", "case",
                                       summary["case_id"], summary)

            prev = (st.session_state["chain"][-1]["chain_hash"]
                    if st.session_state["chain"] else "GENESIS")
            chain_hash = hashlib.sha256(
                f"{prev}:{result['audit_hash']}".encode()).hexdigest()
            st.session_state["chain"].append({
                "case_id": summary["case_id"],
                "audit_hash": result["audit_hash"],
                "chain_hash": chain_hash,
                "prev": prev,
            })
            st.session_state["cases"].append({
                "case": summary["case_id"], "v95": physics["v95"]})

            with st.expander("Exports"):
                with tempfile.TemporaryDirectory() as td:
                    report_path = make_report.build_report(
                        result, Path(td) / "report.html")
                    rt_path = rt_export.export_rtstruct(
                        mask, Path(td) / "rtstruct.dcm")
                    st.download_button("Report (HTML)",
                                       report_path.read_bytes(),
                                       file_name="protonai_report.html",
                                       mime="text/html")
                    st.download_button("RTSTRUCT", rt_path.read_bytes(),
                                       file_name="protonai_rtstruct.dcm",
                                       mime="application/dicom")
                st.download_button(
                    "Summary (JSON)",
                    json.dumps(summary, indent=2, default=str).encode(),
                    file_name="protonai_summary.json", mime="application/json")

            with st.expander("Physician approval"):
                physician = st.text_input("Physician name / ID")
                if st.button("Approve case") and physician.strip():
                    approved = pipeline.approve_case(result, physician.strip())
                    st.session_state["current"] = approved
                    services()["audit"].record(
                        "case.approved", "case", summary["case_id"],
                        {"physician": physician.strip()})
                    st.success(f"Approved by {physician.strip()}")

# ── Tab 2: Optimizer ──────────────────────────────────────
with tabs[1]:
    st.subheader("Robust spot-weight optimizer")
    c = st.columns(4)
    prescription = c[0].slider("Prescription (Gy)", 40.0, 80.0, 70.0, 2.0)
    n_spots = c[1].slider("Spots", 20, 200, 80, 10)
    n_voxels = c[2].slider("Voxels", 500, 5000, 1000, 250)
    oar_weight = c[3].slider("OAR weight", 0.0, 3.0, 1.0, 0.1)

    if st.button("Run optimizer", type="primary"):
        target = np.zeros(n_voxels, dtype=bool)
        target[n_voxels // 3:2 * n_voxels // 3] = True
        oar = np.zeros(n_voxels, dtype=bool)
        oar[2 * n_voxels // 3:] = True
        optimizer = ProtonOptimizer(prescription_gy=prescription,
                                    oar_weight=oar_weight)
        with st.spinner("Optimizing..."):
            opt_result = optimizer.optimize(
                n_spots=n_spots, n_voxels=n_voxels,
                target_mask=target, oar_mask=oar,
                n_scenarios=5, max_iter=150)

        m = st.columns(3)
        m[0].metric("Target D95", f"{opt_result.target_d95:.2f} Gy")
        m[1].metric("Robust D95", f"{opt_result.robust_worst_d95:.2f} Gy")
        m[2].metric("OAR mean", f"{opt_result.oar_mean:.2f} Gy")

        fig, ax = plt.subplots(1, 2, figsize=(11, 4))
        ax[0].plot(opt_result.spot_weights, color="#00ACC1", lw=2)
        ax[0].set_title("Optimized spot weights")
        ax[0].set_xlabel("Spot index")
        ax[1].plot(opt_result.dose, color="#0D47A1", lw=2)
        ax[1].axhline(prescription, color="#C62828", ls="--",
                      label="Prescription")
        ax[1].set_title("Dose distribution")
        ax[1].legend()
        fig.tight_layout()
        st.pyplot(signed(fig))
        st.caption(f"Iterations: {opt_result.iterations} · "
                   f"Converged: {opt_result.converged}")

# ── Tab 3: 3D ─────────────────────────────────────────────
with tabs[2]:
    st.subheader("3D target explorer")
    current = st.session_state["current"]
    if current is None:
        st.info("Run an analysis in the Analysis tab first.")
    else:
        mask = current["masks"][current["rep_slice"]]
        volume = np.zeros((st.session_state["nz"],) + mask.shape)
        volume[6:13] = mask
        if go is not None:
            fig = go.Figure(go.Isosurface(
                value=volume.flatten().astype(float),
                isomin=0.5, isomax=1.0, opacity=0.6,
                surface_count=2, colorscale="Reds"))
            fig.update_layout(height=440,
                              margin=dict(l=0, r=0, t=20, b=0),
                              title="GTV isosurface")
            st.plotly_chart(fig, use_container_width=True)
        else:
            fig = plt.figure(figsize=(7, 5))
            ax = fig.add_subplot(projection="3d")
            ax.voxels(volume[::2, ::2, ::2], facecolors="#FF5252",
                      alpha=0.6)
            ax.set_title("GTV voxels")
            st.pyplot(signed(fig))

# ── Tab 4: CBIR ───────────────────────────────────────────
with tabs[3]:
    st.subheader("Similar case retrieval")
    st.caption("Content-based retrieval across previously analysed cases.")
    current = st.session_state["current"]
    image = st.session_state["image"]
    if current is None or image is None:
        st.info("Run analyses first to build the case database.")
        st.metric("Database size", services()["cbir"].count())
    else:
        rep = current["rep_slice"]
        matches = services()["cbir"].search(
            image[rep], mask=current["masks"][rep], top_k=4)
        st.metric("Database size", services()["cbir"].count())
        if matches:
            st.dataframe(cbir_panel.format_match_table(matches),
                         use_container_width=True)
            fig = cbir_panel.render_similarity_grid(image[rep], matches)
            if fig is not None:
                st.pyplot(fig)
            report = cbir_panel.generate_cbir_report(
                matches, current["summary"]["case_id"])
            st.info(report["recommendation"])
        else:
            st.info("No matches yet.")

# ── Tab 5: GraphQL ────────────────────────────────────────
with tabs[4]:
    st.subheader("GraphQL explorer")
    st.caption("Offline preview of the /graphql contract.")
    query = st.text_area("Query", height=200, value="""{
  cases(limit: 5) {
    caseId
    status
    physics { v95 tcp }
  }
}""")
    if st.button("Execute (offline preview)", type="primary"):
        current = st.session_state["current"]
        data = []
        if current is not None:
            data.append({
                "caseId": current["summary"]["case_id"],
                "status": current.get("status", "completed"),
                "physics": {
                    "v95": current["summary"]["physics"]["v95"],
                    "tcp": current["summary"]["physics"]["tcp"],
                },
            })
        st.json({"data": {"cases": data}, "query": query})

# ── Tab 6: Audit ──────────────────────────────────────────
with tabs[5]:
    st.subheader("Cryptographic audit chain")
    chain = st.session_state["chain"]
    if not chain:
        st.info("No audited cases yet.")
    else:
        valid = True
        previous = "GENESIS"
        for entry in chain:
            expected = hashlib.sha256(
                f"{previous}:{entry['audit_hash']}".encode()).hexdigest()
            if expected != entry["chain_hash"] or entry["prev"] != previous:
                valid = False
            previous = entry["chain_hash"]
        if valid:
            st.success(f"Chain intact — {len(chain)} records verified.")
        else:
            st.error("Chain integrity check FAILED.")
        for i, entry in enumerate(chain):
            with st.expander(f"#{i} · {entry['case_id']}"):
                st.code(f"audit: {entry['audit_hash']}\n"
                        f"chain: {entry['chain_hash']}\n"
                        f"prev:  {entry['prev']}")

    st.divider()
    st.subheader("Persistent audit log")
    log = services()["audit"]
    verification = log.verify_integrity()
    st.write("Integrity:", verification)
    events = log.query(limit=10)
    if events:
        st.dataframe([{"id": e["id"][:8], "action": e["action"],
                       "time": e["timestamp"]} for e in events],
                     use_container_width=True)

# ── Tab 7: Registry ───────────────────────────────────────
with tabs[6]:
    st.subheader("Model registry & drift monitoring")
    registry = services()["registry"]
    if not registry.list_versions():
        card_path = ROOT / "models" / "model_card.json"
        if card_path.exists():
            card = json.loads(card_path.read_text(encoding="utf-8"))
            registry.register(
                "v1.0.0-synthetic",
                metrics={"dice": card.get("test_dice_mean", 0.0),
                         "f1": card.get("test_f1_mean", 0.0)},
                author=DEVELOPER,
                description="Synthetic pretraining baseline",
                dataset_hash="synthetic-v1")
            registry.promote("v1.0.0-synthetic", "production")

    versions = registry.list_versions()
    if versions:
        st.dataframe([{"version": v.version, "stage": v.stage,
                       "dice": v.metrics.get("dice", 0.0),
                       "author": v.author} for v in versions],
                     use_container_width=True)

    st.divider()
    st.subheader("Drift monitor")
    drift = services()["drift"]
    current = st.session_state["current"]
    if current is not None:
        report = drift.check(np.array([
            current["summary"]["uncertainty_mean"],
            current["summary"]["physics"]["v95"]]))
        c = st.columns(3)
        c[0].metric("Severity", report.severity)
        c[1].metric("PSI", f"{report.psi:.4f}")
        c[2].metric("KS", f"{report.ks_stat:.4f}")

    trend = drift.trend(window=30)
    if trend:
        fig, ax = plt.subplots(figsize=(8, 3.5))
        ax.plot([p.get("psi", 0.0) for p in trend],
                marker="o", label="PSI", color="#0D47A1")
        ax.plot([p.get("ks", 0.0) for p in trend],
                marker="s", label="KS", color="#F9A825")
        ax.axhline(0.25, color="#C62828", ls="--", label="High threshold")
        ax.set_title("Drift over time")
        ax.legend()
        fig.tight_layout()
        st.pyplot(signed(fig))

# ── Tab 8: Webhooks ───────────────────────────────────────
with tabs[7]:
    st.subheader("Event notifications")
    st.caption("Notify external systems (EHR / OIS / research DB).")
    manager = services()["webhooks"]

    with st.form("new_subscription"):
        url = st.text_input("Webhook URL", "https://example.com/hook")
        event_types = st.multiselect(
            "Events", ["case.completed", "case.approved", "drift.detected"],
            default=["case.completed"])
        if st.form_submit_button("Subscribe", type="primary") and url.strip():
            subscription = manager.subscribe(url.strip(), event_types)
            st.success(f"Subscribed: {subscription.id[:12]}")

    if manager.subscriptions:
        st.dataframe([{"id": s.id[:12], "url": s.url,
                       "events": ", ".join(s.events),
                       "active": s.active}
                      for s in manager.subscriptions],
                     use_container_width=True)

    if st.button("Emit test event"):
        manager.emit("case.completed",
                     {"case_id": "AHT-PRO-test", "timestamp": time.time()})
        st.success("Event emitted.")

    if manager.deliveries:
        st.dataframe(manager.deliveries[-10:], use_container_width=True)

# ── Footer ───────────────────────────────────────────────
st.divider()
st.caption(f"© 2026 {DEVELOPER} · ProtonAI PRO v{VERSION} · DOI {DOI}")
