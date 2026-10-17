from __future__ import annotations
import hashlib, json, time
from datetime import datetime
import numpy as np
from tools import beam_model, dose_3d, hu_to_spr, plan_metrics, robust, train_seg
from tools.dicom_scrub import scrub, verify_scrubbed

DISCLAIMER = ("Decision-support output. Requires review and approval by a "
              "qualified physician before any clinical use.")


def _compute_dvh(dose, mask, bin_width=0.01):
    d = dose[mask > 0.5]
    if len(d) == 0:
        return {"bins": [], "volumes": [], "D95": 0, "D50": 0, "D5": 0,
                "mean": 0, "max": 0}
    bins = np.arange(0, float(d.max()) + bin_width, bin_width)
    vols = [float((d >= b).sum()) / len(d) for b in bins]
    return {"bins": bins.tolist(), "volumes": vols,
            "D95": float(np.percentile(d, 5)), "D50": float(np.percentile(d, 50)),
            "D5": float(np.percentile(d, 95)), "mean": float(d.mean()),
            "max": float(d.max())}


def _audit(case_id, summary):
    return hashlib.sha256(
        (case_id + ":" + json.dumps(summary, sort_keys=True, default=str)).encode()
    ).hexdigest()


def run_pipeline(image, metadata=None, reference=None,
                 spacing=(1.0, 1.0, 1.0), nz=16, case_id=None):
    if case_id is None:
        case_id = "CASE-" + str(int(time.time()))
    image = np.asarray(image, float)
    if image.ndim < 2 or not np.all(np.isfinite(image)):
        raise ValueError("invalid image: need finite 2D/3D array")
    meta = scrub(metadata or {})
    if not verify_scrubbed(meta):
        raise ValueError("de-identification verification failed")
    model = train_seg.ensure_model()
    masks, uncs = [], []
    for s in range(image.shape[0]):
        m, u = train_seg.predict_unc(model, image[s], n=4)
        masks.append(m); uncs.append(u)
    masks = np.array(masks); uncs = np.array(uncs)
    areas = masks.reshape(masks.shape[0], -1).sum(1)
    rep = int(np.argmax(areas)); mask2d = masks[rep]
    spr2d = np.vectorize(hu_to_spr.hu_to_spr)(image[rep])
    spr3d = np.repeat(spr2d[None], nz, 0)
    t3 = np.zeros((nz,) + mask2d.shape); t3[6:13] = mask2d
    spots = beam_model.spot_lattice(mask2d.shape[0], mask2d.shape[1])
    layers = beam_model.default_layers(t3)
    _, dose = beam_model.optimize_spots((nz,) + mask2d.shape, spots, t3, layers)
    rb = robust.robust_eval(spr3d, mask2d.astype(float), float(layers[-1]), t3)
    dvh = _compute_dvh(dose, t3)
    summary = {
        "case_id": case_id, "n_slices": int(image.shape[0]), "rep_slice": rep,
        "target_volume_voxels": int(areas[rep]),
        "uncertainty_mean": float(uncs[rep].mean()),
        "physics": {"wepl": dose_3d.wepl(spr3d),
                    "r80": plan_metrics.r80(dose.mean((1, 2))),
                    "v95": rb["v95_nominal"],
                    "ci": plan_metrics.conformity(dose, t3),
                    "hi": plan_metrics.homogeneity(dose, t3),
                    "tcp": plan_metrics.tcp_from_dose(dose, t3)},
        "dvh": {k: dvh[k] for k in ("D95", "D50", "D5", "mean", "max")},
        "robust_worst_d95": rb["worst"], "metadata": meta,
        "disclaimer": DISCLAIMER,
        "timestamp": datetime.utcnow().isoformat()}
    if reference is not None:
        summary["dice"] = train_seg.dice(mask2d, np.asarray(reference)[rep])
        summary["hd95"] = train_seg.hd95(mask2d, np.asarray(reference)[rep])
    return {"summary": summary, "masks": masks, "uncertainty": uncs,
            "dose": dose, "dvh": dvh, "audit_hash": _audit(case_id, summary),
            "rep_slice": rep, "metadata": meta}


def approve_case(result, physician, comments=""):
    ap = {"approved_by": physician,
          "approved_at": datetime.utcnow().isoformat(), "comments": comments,
          "signature_hash": hashlib.sha256(
              (result["audit_hash"] + ":" + physician + ":" + comments).encode()
          ).hexdigest()}
    result["approval"] = ap; result["status"] = "APPROVED"
    return result
