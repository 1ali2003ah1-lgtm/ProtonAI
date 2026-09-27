# ProtonAI Experiment Report

## Document Control
| ID | Version | Generated | Generator commit | Status |
|---|---|---|---|---|
| RPT-001 | 2.0 | 2026-09-27 12:13 UTC | 82de338942db | EFFECTIVE |

## 1. Executive Summary
Replacing the Cross-Entropy loss with a combined Dice+CE loss
improves organ-at-risk segmentation accuracy. Verified through the
validated DICOM ingestion pipeline (v0.2.0-ingestion) on the
difficulty-calibrated phantom SYNTH-002, with statistical evidence:
Wilcoxon one-sided p = 0.031250, bootstrap 95%
CI excluding 0, and 3/3 seeds concordant.
**Final verdict: STRONG EVIDENCE: HYPOTHESIS SUPPORTED**

## 2. Hypothesis
Combined Dice+CE loss yields higher Dice than CE alone for
organ-at-risk segmentation in head & neck CT (HYPOTHESIS.md).

## 3. Methods
- Ingestion: DICOM -> DicomReader -> HU pixels (ADR-001).
- Phantoms: SYNTH-001 (ingestion checks); SYNTH-002 calibrated
  (contrast +80 HU, noise 25, irregular lesions, bias field)
  after ceiling-effect discovery (ADR-004).
- Models: baseline torch_segmenter (CE) vs experimental_segmenter
  (Dice+CE); 40 epochs; seeds 42/123/999 for robustness.
- Statistics (ADR-003): Wilcoxon signed-rank (one-sided),
  bootstrap 95% CI, multi-seed concordance.

## 4. Results
### 4.1 Historical run (raw float phantoms, v0.2.0)
- Baseline 0.9994 vs Experiment 1.0000 (delta +0.0006); verdict: HYPOTHESIS SUPPORTED.

### 4.2 Phase-2 pipeline run (SYNTH-002)
| Metric | Value |
|---|---|
| Baseline mean Dice (CE) | 0.9769 |
| Experiment mean Dice (Dice+CE) | 0.9815 |
| Delta | +0.004628 |
| Wilcoxon one-sided p | 0.031250 |
| Bootstrap 95% CI | [+0.000569, +0.010407] |
| Multi-seed (42/123/999) | all SUPPORTED |

![Per-case Dice](docs/experiments/figures/fig_per_case_dice.svg)

![Delta with CI](docs/experiments/figures/fig_delta_ci.svg)

Secondary finding: Dice+CE reduces cross-case variance
(std 0.0087 -> 0.0019): a consistency gain of clinical relevance.

## 5. Evidence Integrity & Provenance
- Artifacts sealed by sha256 in
  docs/experiments/PROVENANCE_synth002.json.
- Integrity enforced by test_experiment_reproducibility.py
  (8 tests, incl. tamper detection).
- Provenance commit: 8fbdadf20345.

## 6. Limitations
- Synthetic phantoms lack real-scanner artifacts; validation on
  clinical CT remains mandatory (RISK_REGISTER R-003).
- Small sample (n=8 per arm); non-parametric methods used.

## 7. Reproducibility
```bash
python tools/make_synthetic_dicom.py --hard
python tools/run_pipeline_experiment.py SYNTH-002 \
    pipeline_experiment_synth002.json
python tools/experiment_statistics.py SYNTH-002 \
    experiment_statistics_synth002.json
python tools/make_provenance_manifest.py
pytest test_experiment_reproducibility.py -q
```

## 8. Governance References
ADR-001 (synthetic-first), ADR-002 (warning policy),
ADR-003 (statistical methods), ADR-004 (ceiling effect &
calibration); RISK_REGISTER R-001..R-008; CAPA_LOG CAPA-001.
