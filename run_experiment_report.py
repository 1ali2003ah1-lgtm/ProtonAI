"""Generate EXPERIMENT_REPORT.md from experiment_results.json (guide step 5)."""
import json
from pathlib import Path

res = json.loads(Path("experiment_results.json").read_text())
base = res["baseline_mean_dice"]
exp = res["experiment_mean_dice"]
delta = res["delta"]
verdict = res["verdict"]

bar = lambda v: "#" * int(round(v * 40))
chart = ("```\n"
         f"baseline   (CE)      | {bar(base)} | {base:.4f}\n"
         f"experiment (Dice+CE) | {bar(exp)} | {exp:.4f}\n"
         "```")

md = f"""# ProtonAI - University Experiment Report

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
| Baseline (CE) | {base:.4f} |
| Experiment (Dice+CE) | {exp:.4f} |

Delta (experiment - baseline): **{delta:+.4f}**

{chart}

- Baseline report: `{res.get('baseline_report')}`
- Experiment report: `{res.get('experiment_report')}`

## 4. Verdict
**{verdict}**

## 5. Limitations
Synthetic phantoms contain easily separable lesions, so the observed delta is
small. Validation on real clinical CT (hospital DICOM / TCIA) is the planned
next step to quantify the real-world gain.

## 6. Reproducibility
```bash
python run_experiment_eval.py
python run_experiment_report.py
```
"""

# Best-effort enrichment with the platform's own paper_builder (guide step 5)
try:
    import inspect
    import paper_builder
    PB = next(o for _, o in inspect.getmembers(paper_builder, inspect.isclass)
              if o.__module__ == "paper_builder" and hasattr(o, "build"))
    repo_stats = PB().collect()
    md += ("\n## 7. Platform-wide statistics (paper_builder)\n```python\n"
           + repr(repo_stats) + "\n```\n")
except Exception as exc:
    print(f"[info] paper_builder enrichment skipped: {exc}")

out = Path("EXPERIMENT_REPORT.md")
out.write_text(md)
print(f"Report saved -> {out}")
print(md[:500])
