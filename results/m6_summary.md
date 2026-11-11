# Milestone 6 results: change detection

Provenance: **SIM** (fast path).

One year of sessions in epochs of 5 nights. Frequency follows temperature (-0.05% per degree C,
assumed) and an unobserved slow term (0.3% RMS, assumed). A permanent stiffness loss is applied half-way.
Half the nights are calm, so many epochs give no estimate. Threshold set for 5% false alarms on loss-free runs.

| Storeys | Phone | Sessions in the year | Epochs with an estimate | Residual scatter | 2.5% loss | 5% loss | 10% loss | 20% loss | Minimum detectable loss (90%) |
|---|---|---|---|---|---|---|---|---|---|
| 9 | low | 40 | 81% | 0.87% | 33% | 47% | 60% | 70% | not reached |
| 9 | low | 60 | 80% | 0.80% | 53% | 80% | 77% | 83% | not reached |
| 9 | low | 100 | 83% | 0.80% | 90% | 100% | 100% | 100% | 2.5% |
| 9 | low | 200 | 84% | 0.70% | 47% | 100% | 97% | 100% | 5% |
| 25 | low | 40 | 55% | 0.80% | 23% | 7% | 13% | 10% | not reached |
| 25 | low | 60 | 55% | 0.77% | 23% | 43% | 43% | 43% | not reached |
| 25 | low | 100 | 60% | 0.63% | 73% | 90% | 83% | 93% | 5% |
| 25 | low | 200 | 59% | 0.69% | 57% | 93% | 100% | 100% | 5% |
| 9 | mid | 40 | 29% | 1.39% | 0% | 13% | 3% | 10% | not reached |
| 9 | mid | 60 | 28% | 0.73% | 10% | 13% | 20% | 30% | not reached |
| 9 | mid | 100 | 34% | 0.91% | 40% | 63% | 70% | 63% | not reached |
| 9 | mid | 200 | 41% | 0.76% | 63% | 67% | 67% | 73% | not reached |

A stiffness loss of 5%, 10% and 20% lowers frequency by 2.5%, 5.1% and 10.6%. Estimated step sizes (median, percent of frequency):

| Storeys | Phone | Sessions | 2.5% loss | 5% loss | 10% loss | 20% loss |
|---|---|---|---|---|---|---|
| 9 | low | 40 | -1.04 | -1.76 | -4.59 | -10.56 |
| 9 | low | 60 | -1.31 | -2.43 | -5.08 | -10.49 |
| 9 | low | 100 | -1.34 | -2.69 | -5.05 | -10.46 |
| 9 | low | 200 | -1.39 | -2.52 | -5.10 | -10.56 |
| 25 | low | 40 | +0.00 | +0.00 | +0.00 | +0.00 |
| 25 | low | 60 | -0.82 | -1.10 | -3.13 | -3.67 |
| 25 | low | 100 | -1.31 | -2.62 | -5.14 | -10.66 |
| 25 | low | 200 | -1.26 | -2.50 | -5.12 | -10.69 |
| 9 | mid | 40 | +0.00 | +0.00 | +0.00 | +0.00 |
| 9 | mid | 60 | +0.00 | +0.00 | +0.00 | +0.00 |
| 9 | mid | 100 | +0.00 | -2.37 | -4.92 | -10.24 |
| 9 | mid | 200 | -1.18 | -2.42 | -4.96 | -10.37 |
