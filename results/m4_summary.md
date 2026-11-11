# Milestone 4 results: artefact rejection

Provenance: **SIM** (time-domain simulation with interference). Thresholds were set on this kind of
data and have to be re-tuned on labelled real sessions.

Set: 48 buildings, 432 sessions of 4 h, three phone models (one with a
self-noise resonance and a 1 Hz tick), persistent HVAC tones and elevator rumble per building, per-night
appliances, mains aliases and footsteps, 25% soft surfaces, calm and windy nights mixed.
Windows kept by the stationarity gate: 100.0%.

**This is the held-out test set.** Thresholds were set on a separate tuning set of the same size and then frozen; on the tuning set, with the thresholds as they stood before the last adjustment, the published non-structural share was 3.3%.

Labels: structural = within 2% of a true mode and not on an injected interference frequency;
non-structural = on an interference frequency, or more than 4% from every true mode; ambiguous = near
both, or 2-4% from a true mode. Ambiguous peaks are excluded from the rates.

| | Candidates (z >= 6) | Accepted as structural |
|---|---|---|
| Structural | 80 | 55 |
| Non-structural | 266 | 6 |
| Ambiguous | 41 | 1 |
| Share non-structural (ambiguous excluded) | 76.9% | **9.8%** |

Structural candidates kept: 68.8%.

## What the product would publish

The lowest three accepted modes inside the plausibility window for the building's height:

| Structural | Non-structural | Ambiguous | Share non-structural |
|---|---|---|---|
| 55 | 2 | 1 | **3.5%** |

Fundamental: the true first mode was among the candidates in 36 of 48 buildings. A fundamental
was reported for 36 buildings: 34 correct (a true first mode in either direction),
2 wrong.

## Non-structural peaks by source

| Source | Candidates | Passed rejection |
|---|---|---|
| other (furniture, blend, noise) | 80 | 5 |
| appliance | 75 | 1 |
| hvac tone | 45 | 0 |
| phone resonance | 41 | 0 |
| phone tick harmonic | 18 | 0 |
| elevator | 7 | 0 |

## Labels assigned

| Truth: label | Count |
|---|---|
| non-structural: rejected:too-narrow | 193 |
| structural: structural | 55 |
| non-structural: rejected:vertical | 43 |
| ambiguous: rejected:too-narrow | 26 |
| non-structural: rejected:unsupported | 14 |
| structural: rejected:unsupported | 12 |
| non-structural: structural | 6 |
| structural: rejected:too-narrow | 6 |
| ambiguous: rejected:vertical | 5 |
| ambiguous: rejected:bursty | 4 |
| structural: rejected:single-session | 4 |
| non-structural: rejected:bursty | 4 |
| ambiguous: rejected:unsupported | 2 |
| non-structural: rejected:weak | 2 |
| non-structural: rejected:tone | 2 |
| non-structural: rejected:single-session | 1 |
| ambiguous: rejected:phone-model | 1 |
| structural: rejected:weak | 1 |
| structural: rejected:too-broad | 1 |
| ambiguous: rejected:weak | 1 |
| ambiguous: structural | 1 |
| ambiguous: rejected:too-broad | 1 |
| non-structural: rejected:too-broad | 1 |
| structural: rejected:phone-model | 1 |

Fleet registry (frequencies one phone model reports across unrelated buildings): `{'mid': [], 'low': [], 'mid_res': [2.9]}`
