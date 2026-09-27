"""P3-S4: model-layer UQ via seed-ensemble disagreement (ADR-006).

Per case: K=5 seed models vote per pixel; uncertainty = mean binary
entropy of vote fraction. Tests: Spearman rho(uncertainty, error),
failure-prediction AUC (Dice < 0.97), and OOD sensitivity
(cross-domain uncertainty > in-domain, Mann-Whitney one-sided).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np
from scipy import stats
from sklearn.metrics import roc_auc_score

from dicom_reader import DicomReader  # noqa: E402
from experimental_segmenter import TorchSegmenter as Experiment  # noqa: E402
import seg_metrics  # noqa: E402

EPOCHS = 40
SEEDS = [42, 123, 999, 7, 2024]
FAIL_THRESH = 0.97


def ingest(name):
    d = ROOT / "data" / "synth_ct" / name
    reader = DicomReader(metadata_keys=["PatientID", "Modality"])
    slices = sorted(d.glob("*.dcm"))
    if not slices:
        raise FileNotFoundError(f"no .dcm in {d}; run make_synthetic_dicom.py")
    hu = np.stack([np.asarray(reader.read(p)["pixels"], dtype=float)
                   for p in slices])
    masks = np.load(d / "ground_truth" / "masks.npy").astype(float)
    return hu, masks


def ensemble_votes(hu_tr, m_tr, hu_te):
    votes = []
    for z in range(hu_te.shape[0]):
        preds = []
        for seed in SEEDS:
            model = Experiment(seed=seed)
            model.fit(hu_tr[z % hu_tr.shape[0]], m_tr[z % m_tr.shape[0]],
                      epochs=EPOCHS)
            preds.append(model.segment(hu_te[z]).astype(float))
        votes.append(np.mean(preds, axis=0))
    return votes


def entropy_map(p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return -(p * np.log(p) + (1 - p) * np.log(1 - p))


def case_metrics(votes, masks):
    unc, err, dice = [], [], []
    for v, m in zip(votes, masks):
        unc.append(float(entropy_map(v).mean()))
        consensus = (v >= 0.5).astype(float)
        d = float(seg_metrics.dice(consensus, m))
        dice.append(d)
        err.append(1.0 - d)
    return np.array(unc), np.array(err), np.array(dice)


def main():
    hu1, m1 = ingest("SYNTH-001")
    hu2, m2 = ingest("SYNTH-002")

    print("In-domain ensemble (train+eval SYNTH-002)...")
    unc_in, err_in, dice_in = case_metrics(ensemble_votes(hu2, m2, hu2), m2)
    print("Cross-domain ensemble (train S1, eval S2)...")
    unc_x, err_x, dice_x = case_metrics(ensemble_votes(hu1, m1, hu2), m2)

    rho_in, p_in = stats.spearmanr(unc_in, err_in)
    rho_x, p_x = stats.spearmanr(unc_x, err_x)
    fail_in = (dice_in < FAIL_THRESH).astype(int)
    fail_x = (dice_x < FAIL_THRESH).astype(int)
    auc_in = float(roc_auc_score(fail_in, unc_in)) \
        if 0 < fail_in.sum() < len(fail_in) else None
    auc_x = float(roc_auc_score(fail_x, unc_x)) \
        if 0 < fail_x.sum() < len(fail_x) else None
    _, u_p = stats.mannwhitneyu(unc_x, unc_in, alternative="greater")

    informative = bool((rho_in > 0 and p_in < 0.05) or (rho_x > 0 and p_x < 0.05)
                       or (auc_in is not None and auc_in >= 0.7)
                       or (auc_x is not None and auc_x >= 0.7))
    ood_sensitive = bool(u_p < 0.05)
    if informative and ood_sensitive:
        verdict = "UNCERTAINTY INFORMATIVE + OOD-SENSITIVE"
    elif informative:
        verdict = "UNCERTAINTY INFORMATIVE (OOD sensitivity not confirmed)"
    elif ood_sensitive:
        verdict = "OOD-SENSITIVE ONLY (error correlation not confirmed)"
    else:
        verdict = "UNCERTAINTY NOT INFORMATIVE"

    print("\n===== UQ ANALYSIS (ADR-006) =====")
    print(f"in-domain : mean_unc={unc_in.mean():.4f} rho={rho_in:+.4f} "
          f"p={p_in:.4f} auc={auc_in}")
    print(f"cross-dom : mean_unc={unc_x.mean():.4f} rho={rho_x:+.4f} "
          f"p={p_x:.4f} auc={auc_x}")
    print(f"OOD test  : Mann-Whitney p={u_p:.4f}")
    print(f"VERDICT: {verdict}")

    artifact = {
        "method": "seed-ensemble disagreement (K=5), pixel-wise vote entropy",
        "seeds": SEEDS, "epochs": EPOCHS, "fail_threshold": FAIL_THRESH,
        "in_domain": {"mean_uncertainty": float(unc_in.mean()),
                      "spearman_rho": float(rho_in), "spearman_p": float(p_in),
                      "auc_failure": auc_in,
                      "per_case_uncertainty": unc_in.tolist(),
                      "per_case_dice": dice_in.tolist()},
        "cross_domain": {"mean_uncertainty": float(unc_x.mean()),
                         "spearman_rho": float(rho_x), "spearman_p": float(p_x),
                         "auc_failure": auc_x,
                         "per_case_uncertainty": unc_x.tolist(),
                         "per_case_dice": dice_x.tolist()},
        "ood_mannwhitney_p": float(u_p),
        "ood_sensitive": ood_sensitive,
        "informative": informative,
        "verdict": verdict,
    }
    (ROOT / "uq_analysis_results.json").write_text(
        json.dumps(artifact, indent=2), encoding="utf-8")
    print("Saved -> uq_analysis_results.json")


if __name__ == "__main__":
    main()
