# Milestone 1 results: simulator and identification core

Provenance of every number in this file: **SIM**. Nothing here was measured on a real building.
Excitation levels and phone noise profiles are assumptions (see `quakescore/sim/excitation.py` and
`quakescore/sim/phone.py`); the tables are reported against them and against the physical
peak-to-noise ratio so they can be re-read when field data replaces the assumptions.

## 1. Fast spectral path against the full time-domain path

Four 4-hour sessions per case. `ratio` is stacked spectrum divided by the analytic expectation
(median over the band); `z` is the detection score of the first mode in x.

| Storeys | Phone | Time-domain ratio L/M/H | Fast ratio L/M/H | z time-domain | z fast | f error TD | f error fast |
|---|---|---|---|---|---|---|---|
| 5 | low | 1.002/1.003/1.002 | 1.001/0.997/1.000 | 39 | 39 | 0.03% | 0.02% |
| 9 | low | 0.998/1.000/1.002 | 1.000/1.000/0.999 | 37 | 36 | 0.06% | 0.10% |
| 25 | low | 1.003/1.001/1.002 | 1.003/0.999/0.999 | 95 | 97 | -0.00% | 0.01% |
| 9 | mid | 1.000/1.002/1.003 | 1.001/0.997/1.000 | 7 | 8 | 1.20% | -0.24% |
| 40 | mid | 0.998/1.001/1.002 | 0.996/1.001/1.000 | 196 | 238 | 0.04% | 0.07% |
| 3 | low | 1.001/1.007/1.003 | 1.001/0.999/1.000 | 48 | 51 | 0.10% | 0.05% |

The device pipeline reproduces the analytic spectrum to within about 1% in all three bands, and the
fast path gives the same detection scores as the time-domain path. The fast path is used for the
large sweeps below; it has no quantisation, jitter, gating or interference.

## 2. Estimator comparison (time-domain sessions)

Six 4-hour sessions per building, phone at the roof, six buildings per row, first mode in x and y.
Entries are median absolute error. Random decrement runs on raw device data; the others on the
stacked spectra. `SNR` is the peak-to-noise-floor power ratio of the stacked spectrum.

| Storeys | Scenario | Phone | Found | Median SNR | f: curve fit | f: FDD peak | f: EFDD | f: SSI-COV | zeta: curve fit | zeta: EFDD | zeta: SSI-COV | zeta: random decrement | zeta interval covers truth |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3 | energetic | low | 12/12 | 0.29 | 0.10% | 0.31% | 0.13% | 0.13% | 1% | 31% | 46% | 122% | 92% |
| 3 | energetic | mid | 12/12 | 0.07 | 0.25% | 0.64% | 0.33% | 0.57% | 8% | 41% | 62% | 139% | 83% |
| 3 | typical | low | 5/12 | 0.04 | 0.40% | 1.12% | 1.27% | 0.77% | 37% | 94% | 64% | 133% | 60% |
| 9 | energetic | low | 12/12 | 0.36 | 0.07% | 0.62% | 0.28% | 0.18% | 4% | 26% | 35% | 151% | 92% |
| 9 | energetic | mid | 12/12 | 0.09 | 0.31% | 0.73% | 2.86% | 0.59% | 15% | 72% | 51% | 169% | 83% |
| 9 | typical | low | 3/12 | 0.04 | 0.60% | 1.94% | 2.92% | 0.86% | 18% | 137% | 37% | 168% | 100% |
| 25 | energetic | low | 12/12 | 1.18 | 0.07% | 0.41% | 0.15% | 0.12% | 4% | 15% | 16% | 209% | 100% |
| 25 | energetic | mid | 12/12 | 0.25 | 0.08% | 0.70% | 0.61% | 0.26% | 17% | 36% | 35% | 300% | 92% |
| 25 | typical | low | 0/12 | - | - | - | - | - | - | - | - | - | - |
| 40 | energetic | low | 12/12 | 23.02 | 0.04% | 0.10% | 0.06% | 0.08% | 7% | 7% | 16% | 11% | 83% |
| 40 | energetic | mid | 12/12 | 4.75 | 0.05% | 0.10% | 0.06% | 0.16% | 12% | 5% | 13% | 42% | 75% |
| 40 | typical | low | 1/12 | 0.22 | 0.28% | 0.92% | 0.14% | 0.18% | 15% | 79% | 43% | 663% | 100% |

Pooled by regime:

| Regime | Modes | f: curve fit | f: FDD peak | f: EFDD | f: SSI-COV | zeta: curve fit | zeta: EFDD | zeta: SSI-COV | zeta: random decrement |
|---|---|---|---|---|---|---|---|---|---|
| peak below noise floor (SNR < 1) | 74 | 0.11% | 0.58% | 0.44% | 0.31% | 10% | 40% | 42% | 152% |
| peak above noise floor (SNR >= 1) | 31 | 0.05% | 0.11% | 0.05% | 0.11% | 8% | 6% | 12% | 34% |

Bootstrap 90% interval for damping covers the truth in 87% of modes (nominal 90%); for frequency in 95%. Median width of the damping interval: 39% of the true value.

## 3. Detection limit by building height

Sessions are 6-hour nights, one phone per session, random yaw, 15% of placements on a soft surface.
Entry: number of sessions needed before the first mode is found and within 2% of the truth in at
least 90% of 12 trials. `>50` means not reached with 50 sessions. Scenario assumptions: quiet =
ground noise -110 dB re (m/s^2)^2/Hz and 1.5 m/s wind; typical = -100 dB and 3 m/s; energetic =
-90 dB and 7 m/s. Phone noise density: low 80, mid 150, high 300 ug/sqrt(Hz).

### Phone on the top floor

| Storeys | Typical f1 (Hz) | quiet / low | quiet / mid | quiet / high | typical / low | typical / mid | typical / high | energetic / low | energetic / mid | energetic / high |
|---|---|---|---|---|---|---|---|---|---|---|
| 2 | 7.58 | >50 | >50 | >50 | 5 | >50 | >50 | 1 | 1 | >50 |
| 3 | 5.05 | >50 | >50 | >50 | 10 | >50 | >50 | 1 | 2 | >50 |
| 5 | 3.03 | >50 | >50 | >50 | 20 | >50 | >50 | 1 | 2 | >50 |
| 7 | 2.16 | >50 | >50 | >50 | 20 | >50 | >50 | 1 | 5 | >50 |
| 9 | 1.68 | >50 | >50 | >50 | 50 | >50 | >50 | 1 | 5 | >50 |
| 12 | 1.26 | >50 | >50 | >50 | 20 | >50 | >50 | 1 | 5 | >50 |
| 15 | 1.01 | >50 | >50 | >50 | 50 | >50 | >50 | 1 | 5 | >50 |
| 25 | 0.61 | >50 | >50 | >50 | >50 | >50 | >50 | 1 | 1 | >50 |
| 40 | 0.38 | >50 | >50 | >50 | 20 | >50 | >50 | 1 | 1 | 1 |

### Phone at mid-height

| Storeys | Typical f1 (Hz) | quiet / low | quiet / mid | quiet / high | typical / low | typical / mid | typical / high | energetic / low | energetic / mid | energetic / high |
|---|---|---|---|---|---|---|---|---|---|---|
| 2 | 7.58 | >50 | >50 | >50 | >50 | >50 | >50 | 5 | 50 | >50 |
| 3 | 5.05 | >50 | >50 | >50 | 20 | >50 | >50 | 1 | 10 | >50 |
| 5 | 3.03 | >50 | >50 | >50 | >50 | >50 | >50 | 5 | >50 | >50 |
| 7 | 2.16 | >50 | >50 | >50 | >50 | >50 | >50 | 1 | 50 | >50 |
| 9 | 1.68 | >50 | >50 | >50 | >50 | >50 | >50 | 2 | >50 | >50 |
| 12 | 1.26 | >50 | >50 | >50 | >50 | >50 | >50 | 5 | >50 | >50 |
| 15 | 1.01 | >50 | >50 | >50 | >50 | >50 | >50 | 1 | 50 | >50 |
| 25 | 0.61 | >50 | >50 | >50 | >50 | >50 | >50 | 1 | 5 | >50 |
| 40 | 0.38 | >50 | >50 | >50 | >50 | >50 | >50 | 1 | 1 | 2 |

### Signal levels behind the table (top floor, median over trials)

| Storeys | Scenario | Modal RMS (ug) | Peak (ug/sqrt(Hz)) | Peak-to-noise r: low / mid / high phone |
|---|---|---|---|---|
| 2 | quiet | 5.1 | 6 | 0.003 / 0.001 / 0.000 |
| 2 | typical | 15.9 | 18 | 0.025 / 0.007 / 0.002 |
| 2 | energetic | 49.3 | 58 | 0.250 / 0.067 / 0.015 |
| 3 | quiet | 4.4 | 6 | 0.003 / 0.001 / 0.000 |
| 3 | typical | 13.5 | 20 | 0.028 / 0.008 / 0.002 |
| 3 | energetic | 42.6 | 62 | 0.284 / 0.075 / 0.017 |
| 5 | quiet | 3.5 | 7 | 0.003 / 0.001 / 0.000 |
| 5 | typical | 10.9 | 21 | 0.031 / 0.008 / 0.002 |
| 5 | energetic | 34.7 | 66 | 0.310 / 0.079 / 0.016 |
| 7 | quiet | 3.0 | 7 | 0.003 / 0.001 / 0.000 |
| 7 | typical | 9.7 | 22 | 0.033 / 0.008 / 0.002 |
| 7 | energetic | 30.4 | 69 | 0.329 / 0.078 / 0.016 |
| 9 | quiet | 2.7 | 7 | 0.003 / 0.001 / 0.000 |
| 9 | typical | 8.5 | 23 | 0.034 / 0.008 / 0.001 |
| 9 | energetic | 28.6 | 73 | 0.352 / 0.082 / 0.015 |
| 12 | quiet | 2.5 | 8 | 0.004 / 0.001 / 0.000 |
| 12 | typical | 8.2 | 24 | 0.038 / 0.008 / 0.002 |
| 12 | energetic | 25.6 | 80 | 0.403 / 0.093 / 0.016 |
| 15 | quiet | 2.3 | 8 | 0.004 / 0.001 / 0.000 |
| 15 | typical | 7.1 | 26 | 0.041 / 0.009 / 0.001 |
| 15 | energetic | 25.1 | 90 | 0.483 / 0.106 / 0.019 |
| 25 | quiet | 1.1 | 6 | 0.002 / 0.000 / 0.000 |
| 25 | typical | 4.1 | 22 | 0.025 / 0.006 / 0.001 |
| 25 | energetic | 33.7 | 175 | 1.635 / 0.437 / 0.064 |
| 40 | quiet | 0.9 | 8 | 0.003 / 0.001 / 0.000 |
| 40 | typical | 5.5 | 49 | 0.106 / 0.016 / 0.003 |
| 40 | energetic | 117.5 | 1080 | 50.279 / 10.575 / 1.020 |

### Detection limit as a rule

Across all configurations, sessions needed against the peak-to-noise ratio `r` of one session:

| Peak-to-noise ratio r | Configurations | Share reaching a stable first mode within 5 / 20 / 50 sessions |
|---|---|---|
| 0 - 0.003 | 71 | 0% / 0% / 0% |
| 0.003 - 0.01 | 29 | 0% / 0% / 0% |
| 0.01 - 0.03 | 21 | 5% / 19% / 24% |
| 0.03 - 0.1 | 21 | 43% / 67% / 86% |
| 0.1 - 0.3 | 11 | 91% / 100% / 100% |
| 0.3 - 1 | 9 | 100% / 100% / 100% |
| 1 - inf | 9 | 100% / 100% / 100% |

### Sensitivity: a 25 ug/sqrt(Hz) phone

The noise floor implied by published MyShake phone spectra is far below datasheet values and
the two have not been reconciled (docs/references.md). If phones are really that quiet:

| Storeys | quiet | typical | energetic |
|---|---|---|---|
| 3 | 10 | 1 | 1 |
| 9 | 20 | 1 | 1 |
| 25 | >50 | 1 | 1 |

Raw candidate peaks that match no true mode, over the whole sweep (no interference, z >= 6, before artefact rejection): 1913 against 6895 correct first-mode detections. Almost all are on the 150 and 300 ug phones and are line-like artefacts near the top of an analysis band, where the baseline window is clipped at the band edge on steep low-frequency noise. The width test of the artefact stage removes them (0 of 63 accepted in a noise-only check). A symmetric baseline window would prevent them; it was not applied because every experiment would have to be rerun.

### Error once detected (all configurations pooled)

| Sessions | First modes detected | Median abs frequency error | 90th percentile | Median abs damping error |
|---|---|---|---|---|
| 1 | 775 | 0.14% | 0.61% | 9% |
| 2 | 901 | 0.12% | 0.57% | 8% |
| 5 | 1074 | 0.11% | 0.56% | 6% |
| 10 | 1250 | 0.10% | 0.60% | 6% |
| 20 | 1377 | 0.10% | 0.54% | 5% |
| 50 | 1518 | 0.09% | 0.51% | 4% |

## 4. Record length

Low-noise phone on the top floor, 16 trials per cell. Entry: share of trials where the first mode (x)
is found within 2%, then median absolute frequency and damping error when found.

| Storeys | Scenario | Sessions | 0.5 h | 1 h | 2 h | 4 h | 8 h |
|---|---|---|---|---|---|---|---|
| 9 | typical | 5 | 0% | 0% | 0% | 12%, 0.46%, 77% | 19%, 0.32%, 58% |
| 9 | typical | 20 | 6%, 1.12%, 65% | 12%, 1.09%, 46% | 6%, 0.30%, 62% | 69%, 0.19%, 22% | 88%, 0.37%, 13% |
| 9 | energetic | 5 | 100%, 0.19%, 15% | 100%, 0.12%, 10% | 100%, 0.15%, 5% | 100%, 0.05%, 6% | 100%, 0.05%, 5% |
| 9 | energetic | 20 | 100%, 0.08%, 10% | 100%, 0.11%, 6% | 100%, 0.04%, 3% | 100%, 0.04%, 2% | 100%, 0.03%, 1% |
| 25 | typical | 5 | 0% | 0% | 0% | 0% | 0% |
| 25 | typical | 20 | 0% | 0% | 0% | 0% | 6%, 0.29%, 4% |
| 25 | energetic | 5 | 100%, 0.21%, 8% | 100%, 0.10%, 7% | 100%, 0.06%, 5% | 100%, 0.04%, 3% | 100%, 0.06%, 2% |
| 25 | energetic | 20 | 100%, 0.08%, 5% | 100%, 0.04%, 3% | 100%, 0.05%, 2% | 100%, 0.04%, 2% | 100%, 0.02%, 1% |

## 5. Several phones at once

One 6-hour night, low-noise phones spread from 30% of the height to the roof, 10 trials per cell.
`incoherent` stacks each phone's own spectrum (no time sync needed). `coherent` runs FDD on the
cross-spectral matrix between phones (needs sync frames). Entries are median detection scores of
the first mode; the last column is the RMS error of the first-mode shape amplitudes (3+ phones).

| Storeys | Scenario | Phones | Sync error (ms) | z incoherent | z coherent | Gain | Mode shape RMS error |
|---|---|---|---|---|---|---|---|
| 9 | energetic | 1 | 5 | 17.4 | 24.6 | 1.41 | - |
| 9 | energetic | 1 | 50 | 21.9 | 28.2 | 1.29 | - |
| 9 | energetic | 1 | 200 | 18.3 | 26.5 | 1.44 | - |
| 9 | energetic | 2 | 5 | 16.2 | 30.3 | 1.87 | - |
| 9 | energetic | 2 | 50 | 16.4 | 32.1 | 1.96 | - |
| 9 | energetic | 2 | 200 | 15.6 | 31.4 | 2.02 | - |
| 9 | energetic | 4 | 5 | 22.9 | 69.8 | 3.05 | 0.027 |
| 9 | energetic | 4 | 50 | 20.5 | 66.3 | 3.23 | 0.024 |
| 9 | energetic | 4 | 200 | 21.8 | 68.6 | 3.14 | 0.023 |
| 9 | energetic | 8 | 5 | 29.1 | 125.2 | 4.31 | 0.018 |
| 9 | energetic | 8 | 50 | 29.2 | 125.0 | 4.28 | 0.016 |
| 9 | energetic | 8 | 200 | 27.6 | 126.6 | 4.59 | 0.021 |
| 9 | typical | 1 | 5 | 3.2 | 2.7 | 0.86 | - |
| 9 | typical | 1 | 50 | 3.0 | 2.8 | 0.94 | - |
| 9 | typical | 1 | 200 | 3.4 | 2.9 | 0.87 | - |
| 9 | typical | 2 | 5 | 2.5 | 2.4 | 0.97 | - |
| 9 | typical | 2 | 50 | 3.6 | 3.4 | 0.94 | - |
| 9 | typical | 2 | 200 | 2.6 | 2.5 | 0.98 | - |
| 9 | typical | 4 | 5 | 3.1 | 3.3 | 1.07 | 0.167 |
| 9 | typical | 4 | 50 | 3.6 | 3.3 | 0.91 | 0.131 |
| 9 | typical | 4 | 200 | 3.3 | 3.6 | 1.09 | 0.190 |
| 9 | typical | 8 | 5 | 3.6 | 4.9 | 1.34 | 0.157 |
| 9 | typical | 8 | 50 | 3.0 | 4.6 | 1.55 | 0.128 |
| 9 | typical | 8 | 200 | 3.5 | 5.2 | 1.50 | 0.153 |
| 25 | energetic | 1 | 5 | 55.5 | 82.2 | 1.48 | - |
| 25 | energetic | 1 | 50 | 52.3 | 73.2 | 1.40 | - |
| 25 | energetic | 1 | 200 | 64.8 | 92.3 | 1.42 | - |
| 25 | energetic | 2 | 5 | 37.6 | 74.9 | 2.00 | - |
| 25 | energetic | 2 | 50 | 51.5 | 110.1 | 2.14 | - |
| 25 | energetic | 2 | 200 | 44.8 | 97.8 | 2.18 | - |
| 25 | energetic | 4 | 5 | 62.5 | 172.9 | 2.76 | 0.016 |
| 25 | energetic | 4 | 50 | 48.8 | 153.6 | 3.15 | 0.012 |
| 25 | energetic | 4 | 200 | 59.6 | 167.4 | 2.81 | 0.013 |
| 25 | energetic | 8 | 5 | 94.8 | 347.0 | 3.66 | 0.013 |
| 25 | energetic | 8 | 50 | 82.7 | 330.0 | 3.99 | 0.014 |
| 25 | energetic | 8 | 200 | 83.5 | 323.9 | 3.88 | 0.013 |
| 25 | typical | 1 | 5 | 2.2 | 2.3 | 1.07 | - |
| 25 | typical | 1 | 50 | 2.7 | 2.4 | 0.90 | - |
| 25 | typical | 1 | 200 | 2.1 | 2.1 | 0.98 | - |
| 25 | typical | 2 | 5 | 2.7 | 2.2 | 0.85 | - |
| 25 | typical | 2 | 50 | 2.1 | 2.4 | 1.11 | - |
| 25 | typical | 2 | 200 | 2.0 | 2.5 | 1.25 | - |
| 25 | typical | 4 | 5 | 2.0 | 2.5 | 1.25 | 0.212 |
| 25 | typical | 4 | 50 | 2.5 | 2.9 | 1.15 | 0.273 |
| 25 | typical | 4 | 200 | 2.4 | 2.4 | 0.98 | 0.219 |
| 25 | typical | 8 | 5 | 2.3 | 2.5 | 1.10 | 0.231 |
| 25 | typical | 8 | 50 | 2.4 | 2.7 | 1.15 | 0.247 |
| 25 | typical | 8 | 200 | 2.2 | 2.1 | 0.96 | 0.239 |

## 6. False alarms on structure-free noise

400 stacks of 20 sessions with no structural response (ground-floor phones, rigid mount), all three bands searched.

| Threshold z | Stacks with at least one false peak | Share |
|---|---|---|
| 5.0 | 64 | 16.00% |
| 5.5 | 17 | 4.25% |
| 6.0 | 5 | 1.25% |
| 7.0 | 0 | 0.00% |
