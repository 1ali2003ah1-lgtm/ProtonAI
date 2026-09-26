# ProtonAI - University Experiment Report

## 1. Hypothesis
Replacing the standard Cross-Entropy loss in `torch_segmenter.py` with a
combined Dice + Cross-Entropy loss improves organ-at-risk segmentation
accuracy (Dice) in head & neck CT cases.

## 2. Methods
- Baseline: `torch_segmenter.py` (CE loss)
- Experiment: `experimental_segmenter.py` (Dice + CE loss)
- Data: 6 synthetic CT phantoms (seeded, reproducible)
- Training: 40 epochs, seed=42, lr=1e-2
- Metrics: `seg_metrics.py` (Dice, HD95, ASSD)

## 3. Results
| Model | Mean Dice |
|---|---|
| Baseline (CE) | 0.9994 |
| Experiment (Dice+CE) | 1.0000 |

Delta (experiment - baseline): **+0.0006**

```
baseline   (CE)      | ######################################## | 0.9994
experiment (Dice+CE) | ######################################## | 1.0000
```

- Baseline report: `{'dice': 0.9990539262062441, 'hd95': 0.0, 'assd': 0.000945179584120983}`
- Experiment report: `{'dice': 1.0, 'hd95': 0.0, 'assd': 0.0}`

## 4. Verdict
**HYPOTHESIS SUPPORTED**

## 5. Limitations
Synthetic phantoms contain easily separable lesions, so the observed delta is
small. Validation on real clinical CT (hospital DICOM / TCIA) is the planned
next step to quantify the real-world gain.

## 6. Reproducibility
```bash
python run_experiment_eval.py
python run_experiment_report.py
```

## 7. Platform-wide statistics (paper_builder)
```python
{'clinical': {'state': 'delivered', 'overall': 'GREEN', 'indicators': [('Gamma Index', '🟢'), ('المدى بالهدف', '🟢'), ('انهيار التغطية', '🟢'), ('المعايير الفيزيائية', '🟢'), ('اكتمال الخطة', '🟢'), ('توقيع المراجعات', '🟢')]}, 'retro': {'n': 5, 'accuracy': 0.8, 'n_correct': 4, 'n_errors': 1, 'errors': [{'predicted': 'M', 'actual': 'B'}], 'confusion': {'TP': 3, 'FP': 1, 'FN': 0, 'TN': 1}, 'sensitivity': 1.0, 'specificity': 0.5, 'ppv': 0.75, 'npv': 1.0}, 'external': {'internal_accuracy': 0.9, 'external_accuracy': 0.88, 'internal_ci': (0.816844242532462, 0.983155757467538), 'external_ci': (0.7899252577022837, 0.9700747422977163), 'n_internal': 50, 'n_external': 50, 'generalization_gap': 0.020000000000000018, 'verdict': 'robust', 'external_acceptable': True, 'publication_ready': True}, 'improvement': {'n_issues': 1}, 'reproducibility': {'seeds': [42], 'python': '3.14.2'}}
```
