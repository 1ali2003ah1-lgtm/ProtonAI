# Head-to-Head Benchmark — BENCHMARK-001

Pooled paired comparisons: n=48 (3 seeds x 16 cases).
Comparators are SIMULATED surrogates; real-commercial head-to-head pending partner data.

| Method | Dice | HD95 | ms/case |
|---|---|---|---|
| protonai | 0.991±0.011 | 0.03 | 4.4 |
| atlas | 0.005±0.009 | 13.74 | 0.0 |
| commercial_sim | 0.494±0.125 | 2.22 | 0.0 |
| manual_sim | 0.708±0.090 | 2.58 | 0.0 |

## Paired comparisons (ProtonAI − comparator)

- vs atlas: p=1.52e-09, CI[0.982, 0.990], Cliff's delta=1.00 => **superior**
- vs commercial_sim: p=1.631e-09, CI[0.463, 0.531], Cliff's delta=1.00 => **superior**
- vs manual_sim: p=7.105e-15, CI[0.259, 0.307], Cliff's delta=1.00 => **superior**
