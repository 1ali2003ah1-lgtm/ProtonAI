"""P4-S3: paired-sample size for the real-data validation study."""
from __future__ import annotations

import math


def paired_n(delta=0.02, sigma=0.03, alpha=0.05, power=0.80,
             wilcoxon_efficiency=0.955):
    z = 1.959964 + 0.841621  # z_{1-alpha/2} + z_{1-beta}
    return math.ceil((z * sigma / delta) ** 2 / wilcoxon_efficiency)


if __name__ == "__main__":
    print(f"n_min={paired_n()} (target=30)")
