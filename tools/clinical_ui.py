from __future__ import annotations
import csv, hashlib, io, json, sys, time, zipfile, tempfile
from datetime import datetime
from pathlib import Path
import numpy as np
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools import beam_model, hu_to_spr, make_report, pipeline, robust, rt_export, train_seg
try:
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except Exception:
    HAS_PLOTLY = False
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DEVELOPER = "Ali Hussein Thajil"
VERSION = "0.9.5-ultra"
DOI = "10.5281/zenodo.23147530"

st.set_page_config(page_title="ProtonAI ULTRA Console", page_icon="🏥", layout="wide")
st.markdown('<style>@keyframes grad{0%{background-position:0% 50%}50%{background-position:100% 50%}100%{background-position:0% 50%}}.hero{background:linear-gradient(135deg,#0D47A1,#1976D2,#00ACC1,#7C4DFF);background-size:300% 300%;animation:grad 9s ease infinite;color:#fff;padding:26px 30px;border-radius:16px;margin-bottom:14px;box-shadow:0 8px 32px rgba(13,71,161,.45)}.hero h1{margin:0;font-size:2.2rem}.hero p{margin:6px 0 0;opacity:.95}.sig{font-size:.85rem;opacity:.9;margin-top:10px;border-top:1px solid rgba(255,255,255,.4);padding-top:8px}.glass{background:rgba(255,255,255,.85);backdrop-filter:blur(8px);border:1px solid rgba(255,255,255,.6);border-radius:14px;padding:14px 16px;box-shadow:0 4px 18px rgba(0,0,0,.08);height:100%}.tl{display:inline-block;width:12px;height:12px;border-radius:50%;margin-right:6px}.tl-g{background:#2E7D32;box-shadow:0 0 8px #2E7D32}.tl-y{background:#F9A825;box-shadow:0 0 8px #F9A825}.tl-r{background:#C62828;box-shadow:0 0 8px #C62828}.footer{text-align:center;color:#666;font-size:.8rem;margin-top:28px;padding-top:12px;border-top:1px solid #e0e0e0}</style>', unsafe_allow_html=True)

for k, v in dict(cases=[], exports=None, current=None, chain=[], last_image=None, last_nz=16).items():
    st.session_state.setdefault(k, v)
st.session_state.setdefault("lang", "en")
LG = {"en": dict(new="🔬 New Analysis", whatif="🧪 What-If Lab", exp="🧭 3D/BEV", hist="📁 History", audit="🔗 Audit", about="ℹ️ About", run="🎲 Demo", approve="Approve", dl="📥 Downloads"),
      "ar": dict(new="🔬 تحليل", whatif="🧪 مختبر", exp="🧭 مستكشف", hist="📁 سجل", audit="🔗 تدقيق", about="ℹ️ حول", run="🎲 تجريبي", approve="اعتماد", dl="📥 تنزيل")}
L = LG[st.session_state.lang]

@st.cache_resource
def _model(): return train_seg.ensure_model()

def _sig(fig):
    fig.text(.99, .01, "(c) " + DEVELOPER + " - ProtonAI", ha="right", fontsize=6, color="#888")
    return fig

def _overlay(img2d, mask2d):
    fig, ax = plt.subplots(1, 2, figsize=(10, 5))
    ax[0].imshow(img2d, cmap="gray"); ax[0].set_title("CT"); ax[0].axis("off")
    ax[1].imshow(img2d, cmap="gray")
    ax[1].contour(mask2d, colors="#FF1744", linewidths=1.3)
    ax[1].set_title("AI contour"); ax[1].axis("off")
    fig.tight_layout(); return _sig(fig)

def _unc_fig(u):
    fig, ax = plt.subplots(figsize=(5, 5))
    im = ax.imshow(u, cmap="magma"); fig.colorbar(im, ax=ax, fraction=.046)
    ax.set_title("Uncertainty"); ax.axis("off"); return _sig(fig)

def _radar(vals, labels):
    fig = plt.figure(figsize=(5, 5)); ax = fig.add_subplot(polar=True)
    a = np.linspace(0, 2*np.pi, len(vals), endpoint=False).tolist()
    vals = list(vals) + [vals[0]]; a += a[:1]
    ax.plot(a, vals, lw=2.2, color="#00E5FF"); ax.fill(a, vals, alpha=.25)
    ax.set_xticks(a[:-1]); ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylim(0, 1); ax.set_title("Plan quality", fontsize=10); return _sig(fig)

def _bev(t3):
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.imshow(t3.sum(0), cmap="hot")
    lat = np.asarray(beam_model.spot_lattice(t3.shape[1], t3.shape[2]))
    if lat.ndim == 2 and lat.shape[1] == 2:
        ys, xs = lat[:, 0], lat[:, 1]
    else:
        ys, xs = lat
    ax.scatter(xs, ys, s=14, c="#00E5FF", edgecolors="w", linewidths=.4)
    ax.set_title("BEV + spots"); ax.axis("off"); return _sig(fig)

def _iso3d(m):
    if HAS_PLOTLY:
        f = go.Figure(go.Isosurface(value=m.flatten().astype(float), isomin=.5, isomax=1, opacity=.55, surface_count=2, colorscale="Reds"))
        f.update_layout(title="GTV 3D", height=420, margin=dict(l=0, r=0, t=30, b=0))
        return f
    fig = plt.figure(figsize=(5, 5)); ax = fig.add_subplot(projection="3d")
    ax.voxels(m[::2, ::2, ::2], facecolors="#FF5252", alpha=.6)
    ax.set_title("GTV voxels"); return _sig(fig)

def _tl(v, good, warn, hb=True):
    if hb: c = "tl-g" if v >= good else ("tl-y" if v >= warn else "tl-r")
    else: c = "tl-g" if v <= good else ("tl-y" if v <= warn else "tl-r")
    return '<span class="tl ' + c + '"></span>'

with st.sidebar:
    st.markdown("### 🏥 ProtonAI ULTRA\n**v" + VERSION + "**")
    st.caption("Designed & developed by **" + DEVELOPER + "**")
    st.session_state.lang = st.select_slider("Language", ["en", "ar"], value=st.session_state.lang)
    try:
        card = json.loads((ROOT / "models" / "model_card.json").read_text(encoding="utf-8"))
        st.success("Model loaded")
        st.metric("Test Dice", str(round(card.get("test_dice_mean", 0), 4)))
    except Exception as e:
        st.error("Model unavailable: " + str(e)); st.stop()
    ctv = st.checkbox("Generate CTV (+5mm)", value=True)
    nz = st.slider("Z-slices", 8, 32, 16)
    unc_thr = st.slider("Unc alert", .05, .5, .2)
    cs = st.session_state.cases
    a1, a2 = st.columns(2)
    a1.metric("Cases", len(cs))
    a2.metric("Approved", sum(1 for c in cs if c.get("status") == "APPROVED"))

st.markdown('<div class="hero"><h1>🏥 ProtonAI - ULTRA Clinical Console</h1><p>Segmentation - proton dose - DVH - robustness - 3D - audit</p><div class="sig">Designed & developed by <b>' + DEVELOPER + '</b> - v' + VERSION + ' - DOI ' + DOI + '</div></div>', unsafe_allow_html=True)

tabs = st.tabs([L["new"], L["whatif"], L["exp"], L["hist"], L["audit"], L["about"]])

with tabs[0]:
    mode = st.radio("Source", ["Demo", "Upload .npy", "Upload DICOM ZIP"], horizontal=True)
    image, metadata = None, {}
    if mode == "Demo":
        if st.button(L["run"], type="primary"):
            img, _ = train_seg.make_sample(np.random.default_rng(int(time.time()) % 10000))
            image = img[None]; metadata = {"PatientName": "DEMO"}
    elif mode == "Upload .npy":
        up = st.file_uploader("CT .npy", type=["npy"])
        if up is not None: image = np.load(io.BytesIO(up.read()))
    else:
        up = st.file_uploader("DICOM ZIP", type=["zip"])
        if up is not None:
            with tempfile.TemporaryDirectory() as td:
                with zipfile.ZipFile(io.BytesIO(up.read())) as zf:
                    zf.extractall(td)
                from tools import dicom_reader
                d = Path(td)
                for q in [d] + sorted(d.rglob("*")):
                    if q.is_dir() and list(q.glob("*.dcm")): d = q; break
                image, metadata = dicom_reader.read_dicom_series(d)
    if image is not None:
        with st.status("Pipeline running", expanded=True) as stx:
            t0 = time.time()
            result = pipeline.run_pipeline(image, metadata, nz=nz, case_id="AHT-" + str(int(time.time())))
            stx.update(label="Complete in " + str(round(time.time() - t0, 2)) + "s", state="complete")
        st.session_state.current = result
        st.session_state.last_image = image
        st.session_state.last_nz = nz
        s = result["summary"]; p = s["physics"]; rep = result["rep_slice"]
        if s["uncertainty_mean"] > unc_thr:
            st.warning("High uncertainty " + str(round(s["uncertainty_mean"], 4)))
        k = st.columns(5)
        k[0].markdown('<div class="glass">' + _tl(p["v95"], .95, .9) + '<b>V95</b><br><span style="font-size:1.4rem">' + str(round(p["v95"], 3)) + '</span></div>', unsafe_allow_html=True)
        k[1].markdown('<div class="glass">' + _tl(p["tcp"], .9, .8) + '<b>TCP</b><br><span style="font-size:1.4rem">' + str(round(p["tcp"], 3)) + '</span></div>', unsafe_allow_html=True)
        k[2].markdown('<div class="glass">' + _tl(s["robust_worst_d95"], .9, .85) + '<b>Rob D95</b><br><span style="font-size:1.4rem">' + str(round(s["robust_worst_d95"], 3)) + '</span></div>', unsafe_allow_html=True)
        k[3].markdown('<div class="glass">' + _tl(s["uncertainty_mean"], .1, .2, False) + '<b>Unc</b><br><span style="font-size:1.4rem">' + str(round(s["uncertainty_mean"], 4)) + '</span></div>', unsafe_allow_html=True)
        k[4].markdown('<div class="glass"><b>Vol</b><br><span style="font-size:1.4rem">' + str(s["target_volume_voxels"]) + '</span> vox</div>', unsafe_allow_html=True)
        zi = st.slider("Slice", 0, image.shape[0] - 1, rep)
        g = st.columns(4)
        with g[0]: st.pyplot(_overlay(image[zi], result["masks"][zi]))
        with g[1]: st.pyplot(_unc_fig(result["uncertainty"][zi]))
        with g[2]:
            dv = result.get("dvh") or {}
            if dv.get("bins") and HAS_PLOTLY:
                fg = go.Figure(go.Scatter(x=dv["bins"], y=np.array(dv["volumes"]) * 100, fill="tozeroy", line=dict(color="#00B0FF")))
                fg.update_layout(height=320, margin=dict(l=0, r=0, t=10, b=0))
                st.plotly_chart(fg, use_container_width=True)
            elif dv.get("bins"):
                fig, ax = plt.subplots(figsize=(6, 4))
                ax.plot(dv["bins"], np.array(dv["volumes"]) * 100, lw=2)
                ax.set_title("DVH"); st.pyplot(_sig(fig))
        with g[3]: st.pyplot(_radar([min(p["v95"], 1), min(p["ci"], 1), 1 - min(p["hi"], 1), min(p["tcp"], 1), min(s["robust_worst_d95"], 1)], ["V95", "CI", "1-HI", "TCP", "Rob"]))
        with tempfile.TemporaryDirectory() as td:
            rb_ = make_report.build_report(result, Path(td) / "r.html")
            report_b = rb_.read_bytes()
            rt_ = rt_export.export_rtstruct(result["masks"][rep], Path(td) / "rt.dcm", generate_ctv=ctv)
            rt_b = rt_.read_bytes()
        js_b = json.dumps(s, indent=2, default=str).encode()
        buf = io.StringIO(); w = csv.writer(buf)
        w.writerow(["dose_bin", "volume_frac"])
        for b, v in zip((result.get("dvh") or {}).get("bins", []), (result.get("dvh") or {}).get("volumes", [])):
            w.writerow([b, v])
        dvh_b = buf.getvalue().encode()
        cont_b = "\n".join(map(str, rt_export._boundary_points(result["masks"][rep]))).encode()
        readme_b = ("ProtonAI case " + s["case_id"] + "\nDeveloped by " + DEVELOPER + "\nDOI " + DOI + "\naudit " + result.get("audit_hash", "") + "\n").encode()
        zb = io.BytesIO()
        with zipfile.ZipFile(zb, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("report.html", report_b); z.writestr("rtstruct.dcm", rt_b)
            z.writestr("summary.json", js_b); z.writestr("dvh.csv", dvh_b)
            z.writestr("contour.csv", cont_b); z.writestr("README.txt", readme_b)
        st.session_state.exports = dict(report=report_b, rt=rt_b, js=js_b, zip=zb.getvalue(), case=s["case_id"])
        with st.form("appr"):
            phys = st.text_input("Physician name / ID")
            comm = st.text_area("Comments")
            ok = st.form_submit_button(L["approve"], type="primary")
            if ok and phys:
                result = pipeline.approve_case(result, phys, comm)
                st.session_state.current = result
                with tempfile.TemporaryDirectory() as td:
                    st.session_state.exports["report"] = make_report.build_report(result, Path(td) / "r.html").read_bytes()
                st.success("Approved by " + phys)
        st.session_state.cases.append(dict(case=s["case_id"], time=datetime.utcnow().strftime("%H:%M:%S"), v95=round(p["v95"], 3), tcp=round(p["tcp"], 3), status=result.get("status", "PENDING"), summary=s))
        prev = st.session_state.chain[-1]["chain"] if st.session_state.chain else "GENESIS"
        st.session_state.chain.append(dict(case=s["case_id"], audit=result["audit_hash"], chain=hashlib.sha256((prev + ":" + result["audit_hash"]).encode()).hexdigest(), prev=prev))
        e = st.session_state.exports
        d = st.columns(4)
        d[0].download_button("📦 Bundle ZIP", e["zip"], file_name=e["case"] + "_bundle.zip", mime="application/zip", type="primary")
        d[1].download_button("📄 Report", e["report"], file_name=e["case"] + "_report.html", mime="text/html")
        d[2].download_button("🏥 RTSTRUCT", e["rt"], file_name=e["case"] + "_rtstruct.dcm", mime="application/dicom")
        d[3].download_button("🧾 JSON", e["js"], file_name=e["case"] + "_summary.json", mime="application/json")

with tabs[1]:
    res = st.session_state.current
    if res is None: st.info("Run an analysis first.")
    else:
        img = st.session_state.last_image; rep = res["rep_slice"]; m2 = res["masks"][rep]
        spr2 = np.vectorize(hu_to_spr.hu_to_spr)(img[rep])
        nzz = st.session_state.last_nz
        spr3 = np.repeat(spr2[None], nzz, 0)
        t3 = np.zeros((nzz,) + m2.shape); t3[6:13] = m2
        R = float(beam_model.default_layers(t3)[-1])
        c = st.columns(3)
        setup = c[0].slider("Setup shift (mm)", -5., 5., 0., .5)
        rng = c[1].slider("Range error (%)", -5., 5., 0., .5)
        c[2].slider("Margin (mm)", 0., 10., 0., 1.)
        rb = robust.robust_eval(spr3 * (1 + rng / 100), np.roll(m2.astype(float), int(setup), 0), R, t3)
        st.metric("Worst D95", str(round(rb["worst"], 3)))
        st.progress(float(np.clip(rb["worst"], 0, 1)))

with tabs[2]:
    res = st.session_state.current
    if res is None: st.info("Run analysis first.")
    else:
        m2 = res["masks"][res["rep_slice"]]
        m3 = np.zeros((st.session_state.last_nz,) + m2.shape); m3[6:13] = m2
        e1, e2 = st.columns(2)
        with e1:
            f = _iso3d(m3)
            if HAS_PLOTLY: st.plotly_chart(f, use_container_width=True)
            else: st.pyplot(f)
        with e2: st.pyplot(_bev(m3))

with tabs[3]:
    if st.session_state.cases:
        st.dataframe([{k: v for k, v in c.items() if k != "summary"} for c in st.session_state.cases], use_container_width=True)
    else: st.info("No cases yet.")

with tabs[4]:
    if not st.session_state.chain: st.info("No audited cases.")
    else:
        for i, e in enumerate(st.session_state.chain):
            st.markdown('<div class="glass">#' + str(i) + ' <b>' + e["case"] + '</b><br>audit <code>' + e["audit"][:28] + '...</code><br>chain <code>' + e["chain"][:28] + '...</code></div>', unsafe_allow_html=True)
        if st.button("🔍 Verify chain"):
            okc, prev = True, "GENESIS"
            for e in st.session_state.chain:
                exp = hashlib.sha256((prev + ":" + e["audit"]).encode()).hexdigest()
                okc &= (exp == e["chain"] and e["prev"] == prev)
                prev = e["chain"]
            st.success("✅ Chain intact" if okc else "❌ Broken!")

with tabs[5]:
    st.markdown("## 🏥 ProtonAI ULTRA v" + VERSION + "\n**Designed & developed by: " + DEVELOPER + "**\n\nMost advanced open proton therapy console: AI segmentation, proton SOBP, DVH, 9-scenario robustness, what-if lab, 3D/BEV, DICOM RTSTRUCT, signable reports, audit chain.\n\n- DOI `" + DOI + "` - MIT License\n- MDR Class IIb decision-support\n\n> Decision-support only: physician approval required.\n\n---\n(c) 2026 " + DEVELOPER + ". All rights reserved.")

st.markdown('<div class="footer">(c) 2026 <b>' + DEVELOPER + '</b> - ProtonAI v' + VERSION + ' - DOI ' + DOI + '</div>', unsafe_allow_html=True)
