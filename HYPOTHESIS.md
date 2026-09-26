# Research Hypothesis (ProtonAI University Experiment)

Modifying the loss function in torch_segmenter.py from standard
Cross-Entropy to a combined Dice + Cross-Entropy loss will improve
segmentation accuracy (Dice score) of the parotid gland (organ at
risk) in head & neck CT cases.

- Baseline:    standard CE loss   (torch_segmenter.py)
- Experiment:  Dice + CE loss     (experimental_segmenter.py)
- Metric:      Dice coefficient   (seg_metrics.py)
