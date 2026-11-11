# Milestone 5 results: vulnerability model

Class parameters: **REF** (Hazus 6.1). Adjustments for measured period, drift concentration and damping:
**ASSUMED** physics, not calibrated against observed damage. Experiments: **SIM**.

QuakeScore = 100 x (1 - scenario-weighted structural mean damage ratio); scenarios PGA 0.15, 0.30, 0.60 g
with weights 0.3, 0.4, 0.3; 100 is least vulnerable.

## 1. Class baseline at typical height (no measurement)

| Type | Height (m) | Te (s) | High-code | Moderate | Low | Pre-code |
|---|---|---|---|---|---|---|
| C1H | 36.6 | 1.45 | 86.3 | 71.2 | 56.8 | 48.9 |
| C1L | 6.1 | 0.4 | 89.1 | 74.3 | 54.2 | 46.4 |
| C1M | 15.2 | 0.75 | 90.9 | 79.3 | 61.1 | 53.3 |
| C2H | 36.6 | 1.09 | 92.1 | 84.4 | 69.6 | 61.8 |
| C2L | 6.1 | 0.35 | 92.4 | 80.4 | 62.1 | 54.2 |
| C2M | 15.2 | 0.56 | 94.3 | 85.4 | 68.8 | 61.2 |
| C3H | 36.6 | 1.09 | 60.6 | 60.6 | 60.6 | 52.6 |
| C3L | 6.1 | 0.35 | 53.3 | 53.3 | 53.3 | 45.2 |
| C3M | 15.2 | 0.56 | 60.3 | 60.3 | 60.3 | 52.0 |
| PC2M | 15.2 | 0.56 | 91.5 | 80.4 | 62.0 | 53.6 |
| RM1L | 6.1 | 0.35 | 91.1 | 79.0 | 61.4 | 53.2 |
| RM2M | 15.2 | 0.56 | 92.9 | 84.1 | 68.1 | 59.9 |
| S1H | 47.5 | 2.21 | 85.1 | 72.3 | 61.5 | 53.1 |
| S1L | 7.3 | 0.5 | 90.8 | 76.2 | 56.1 | 47.7 |
| S1M | 18.3 | 1.08 | 88.7 | 75.2 | 58.1 | 49.6 |
| S2H | 47.5 | 1.77 | 88.5 | 81.6 | 69.6 | 61.6 |
| S2L | 7.3 | 0.4 | 91.7 | 80.1 | 61.2 | 52.3 |
| S2M | 18.3 | 0.86 | 91.7 | 83.5 | 67.1 | 58.5 |
| URML | 4.6 | 0.35 | 62.5 | 62.5 | 62.5 | 55.1 |
| URMM | 10.7 | 0.5 | 59.6 | 59.6 | 59.6 | 51.4 |
| W1 | 4.3 | 0.35 | 93.2 | 88.1 | 80.9 | 75.2 |

## 2. Sensitivity of the score to measured quantities

**C1M/moderate**

| Stiffness ratio | 0.5 | 0.7 | 0.85 | 1.0 | 1.2 | 1.5 |
|---|---|---|---|---|---|---|
| Score | 75.7 | 77.7 | 78.6 | 79.3 | 79.9 | 80.6 |

| Drift concentration ratio | 1.0 | 1.25 | 1.5 | 2.0 | 3.0 |
|---|---|---|---|---|---|
| Score | 79.3 | 74.2 | 69.7 | 62.0 | 50.2 |

| Damping ratio (measured / expected) | 0.5 | 1.0 | 2.0 |
|---|---|---|---|
| Score | 77.4 | 79.3 | 81.6 |

**C2M/moderate**

| Stiffness ratio | 0.5 | 0.7 | 0.85 | 1.0 | 1.2 | 1.5 |
|---|---|---|---|---|---|---|
| Score | 82.6 | 84.2 | 84.9 | 85.4 | 85.9 | 86.4 |

| Drift concentration ratio | 1.0 | 1.25 | 1.5 | 2.0 | 3.0 |
|---|---|---|---|---|---|
| Score | 85.4 | 81.3 | 77.5 | 70.7 | 59.8 |

| Damping ratio (measured / expected) | 0.5 | 1.0 | 2.0 |
|---|---|---|---|
| Score | 83.9 | 85.4 | 87.2 |

**S1H/moderate**

| Stiffness ratio | 0.5 | 0.7 | 0.85 | 1.0 | 1.2 | 1.5 |
|---|---|---|---|---|---|---|
| Score | 66.5 | 69.6 | 71.1 | 72.3 | 73.4 | 74.7 |

| Drift concentration ratio | 1.0 | 1.25 | 1.5 | 2.0 | 3.0 |
|---|---|---|---|---|---|
| Score | 72.3 | 66.0 | 60.5 | 51.4 | 38.5 |

| Damping ratio (measured / expected) | 0.5 | 1.0 | 2.0 |
|---|---|---|---|
| Score | 70.8 | 72.3 | 74.3 |

**C3M/pre**

| Stiffness ratio | 0.5 | 0.7 | 0.85 | 1.0 | 1.2 | 1.5 |
|---|---|---|---|---|---|---|
| Score | 50.3 | 51.2 | 51.7 | 52.0 | 52.3 | 52.5 |

| Drift concentration ratio | 1.0 | 1.25 | 1.5 | 2.0 | 3.0 |
|---|---|---|---|---|---|
| Score | 52.0 | 46.4 | 41.8 | 34.8 | 25.6 |

| Damping ratio (measured / expected) | 0.5 | 1.0 | 2.0 |
|---|---|---|---|
| Score | 49.2 | 52.0 | 55.3 |

**URMM/pre**

| Stiffness ratio | 0.5 | 0.7 | 0.85 | 1.0 | 1.2 | 1.5 |
|---|---|---|---|---|---|---|
| Score | 49.5 | 50.6 | 51.1 | 51.4 | 51.8 | 52.1 |

| Drift concentration ratio | 1.0 | 1.25 | 1.5 | 2.0 | 3.0 |
|---|---|---|---|---|---|
| Score | 51.4 | 45.7 | 41.0 | 33.9 | 24.5 |

| Damping ratio (measured / expected) | 0.5 | 1.0 | 2.0 |
|---|---|---|---|
| Score | 48.1 | 51.4 | 55.5 |

**W1/moderate**

| Stiffness ratio | 0.5 | 0.7 | 0.85 | 1.0 | 1.2 | 1.5 |
|---|---|---|---|---|---|---|
| Score | 82.0 | 85.5 | 87.1 | 88.1 | 89.2 | 90.2 |

| Drift concentration ratio | 1.0 | 1.25 | 1.5 | 2.0 | 3.0 |
|---|---|---|---|---|---|
| Score | 88.1 | 85.0 | 82.0 | 76.8 | 68.1 |

| Damping ratio (measured / expected) | 0.5 | 1.0 | 2.0 |
|---|---|---|---|
| Score | 86.7 | 88.1 | 89.8 |

## 3. What a measured period adds

Over 200 random buildings: median width of the 5-95% score band is 15.7 points from public
attributes alone and 8.9 points with a measured first-mode period. The score moves by a median of
2.9 points and by more than 9.1 points for one building in ten.

## 4. Stiffness-anomaly detector, height known only

A flag is raised when the building is more than 2 sigma softer than every plausible class.

| True stiffness relative to class | Flagged | Median z under the most probable class |
|---|---|---|
| as expected (false-flag rate) | 0.8% | -0.01 |
| 30% softer | 4.2% | +0.35 |
| 50% softer | 11.9% | +0.71 |
| 65% softer | 28.9% | +1.27 |
| 75% softer | 49.5% | +1.99 |

With height alone, class scatter (sigma of ln T = 0.25) hides all but gross anomalies: a building 30% softer
than expected is flagged about 4% of the time. The detector needs better covariates (plan dimensions, wall
density, known system) to become useful; tracking a building against itself over time is far more sensitive
(Milestone 6).

## 5. Soft-storey indicator from mode shapes

Five nights of synchronised frames, phones spread over the height, first storey at 30% of regular stiffness.
Indicator: share of roof displacement reached at the lowest phone, relative to a regular reference shape.

| Storeys | Phones | Nights | Regular (median) | Soft storey (median) | Detected at 5% false alarms |
|---|---|---|---|---|---|
| 5 | 3 | energetic | 0.73 | 1.65 | 100% |
| 5 | 3 | typical | 1.12 | 1.82 | 85% |
| 5 | 5 | energetic | 0.72 | 1.65 | 100% |
| 5 | 5 | typical | 1.08 | 1.95 | 100% |
| 9 | 3 | energetic | 0.79 | 2.04 | 100% |
| 9 | 3 | typical | 2.21 | 3.00 | 35% |
| 9 | 5 | energetic | 0.81 | 2.03 | 100% |
| 9 | 5 | typical | 1.82 | 2.78 | 65% |

## 6. Validation against observed damage

Not done. No open dataset pairs a pre-earthquake modal measurement with a post-earthquake damage grade for
the same building, so the measured-period adjustment cannot be tested building by building. What is possible
next: a class-level comparison against the ACI 133 Turkey 2023 reinforced-concrete database (about 240
buildings with storeys, height and damage grade, CC BY 4.0), and expert ratings on a test set. See
docs/references.md and docs/REPORT.md.
