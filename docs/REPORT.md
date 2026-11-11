# QuakeScore: final report

Date: 11 November 2026. Labels: `REAL` measured on a real building, `SIM` simulator, `REF` cited
publication, `ASSUMED` assumption not yet measured.

## The short version

The whole chain is built: simulator, on-device feature pipeline, identification, artefact rejection,
vulnerability model, change detection, API, dashboard, collector app sources and a technical note for
buyers. All of it is measured in simulation. None of it has touched a real building. Milestones 2 and
3 need phones in buildings and a compiled app, and neither was possible here: the machine had no Java
or Android toolchain, and field sessions take nights, not compute. So the honest answer to "does it
work" is: the mathematics works under stated assumptions, and the two assumptions that decide the
business (how noisy phones really are, how hard buildings really shake at night) are still unmeasured.

Three things in the starting brief did not survive the literature check (`docs/references.md`):

1. The Millikan Library phone study (Kong et al. 2018) was a forced shaker test, not ambient.
2. The 2023 MyShake paper used earthquake-triggered recordings and judged ambient measurement
   infeasible at phone noise levels.
3. No statement that the Berkeley group lists insurers as an application was found in the papers.
   It should not be repeated to a buyer without a source.

The one ambient phone study that exists (Kumar et al. 2025) covers four tall buildings, and that is
consistent with what the simulator says: tall and windy is the easy case.

## 1. What works on real buildings

Nothing has been measured on a real building. Count of real sessions: 0. Count of real buildings: 0.

| Target | Minimum | Stretch | Measured |
|---|---|---|---|
| First-mode frequency error against reference, 5+ real buildings | within 10% | within 5% | not measured (0 buildings) |
| Sessions for a stable first mode, mid-rise | 20 or fewer | 5 or fewer | SIM only, 9 storeys, top floor: 1 (80 ug phone) to 5 (150 ug) on windy nights; 50 or more on typical nights; not reached on quiet nights |
| Minimum detectable stiffness change | 10% | 5% | SIM only, 9 storeys, 80 ug phone: 5% with 100 or more sessions a year; not reached with 60 sessions or with a 150 ug phone |
| False positives from non-structural peaks | under 5% of reported modes | under 1% | SIM only: 3.5% of published modes on a held-out simulated set (minimum met, stretch not) |
| Phone battery cost per overnight session | under 3% | under 1% | not measured (app never run) |
| Buildings scored in the demo city | 50 | 500 | 0 real; SIM: 222 of 687 under the assumed adoption |

## 2. What works in simulation

All numbers below are `SIM`. Tables: `results/m1_summary.md` to `results/m6_summary.md`,
`results/demo_city_summary.md`.

**Simulator and pipeline (Milestone 1).** A time-domain simulator (shear buildings of 1-40 storeys,
wind and ground forcing, phone noise, quantisation, non-nominal rate, jitter, tilt, furniture
coupling) feeds the same pipeline the phone runs. The processed spectrum matches the analytic
expectation within 1% in all three bands. A fast spectral path reproduces the time-domain detection
scores and is used for large sweeps.

**Identification.** Five estimators were compared on time-domain sessions. With the peak below the
sensor noise floor, the spectral curve fit has a median frequency error of 0.11% and damping error of
10%; SSI-COV 0.31% and 42%; EFDD 0.44% and 40%; FDD peak picking 0.58%; random decrement is unusable
for damping (152%). With the peak above the floor all methods reach about 0.1% in frequency. Bootstrap
intervals, after a small-sample and model-error correction, cover the truth in 95% (frequency) and
87% (damping) of cases at a nominal 90%. Damping intervals are wide: typically 39% of the value.

**Detection limit.** Nights needed for a stable first mode (found within 2% in 90% of trials), phone on the top floor: on a windy or busy night an 80 ug/sqrt(Hz) phone needs 1 night at every height from 2 to 40 storeys, a 150 ug phone 1 to 5, and a 300 ug phone does not get there in 50 nights except at 40 storeys. On a typical night only the 80 ug phone gets there, in 10 nights at 3 storeys, 50 at 9, 50 at 15 and 20 at 40, and not at 25. On a quiet night nothing is found within 50 nights. At mid-height the 150 ug phone needs 10 to more than 50 nights for buildings up to 15 storeys, even when it is windy. The governing quantity is the peak-to-noise power ratio of one night: above 0.1 detection takes a few nights, below 0.01 it does not happen. If phones are as quiet as published fleet spectra imply (25 ug/sqrt(Hz)), one typical night is enough at 3, 9 and 25 storeys. Excitation levels and phone noise are assumptions, so this table is a map of what has to be measured, not a forecast.

A defect to know about: on phones with steep low-frequency noise the raw candidate list contains line-like artefacts near the top of each analysis band, caused by the baseline window being clipped at the band edge (1913 raw candidates in the sweep match no true mode, almost all on the 150 and 300 ug phones). The width test removes them (0 of 63 accepted in a noise-only check of 60 stacks). The fix, a symmetric baseline window, is known and was not applied because it would require rerunning every experiment.

**Record length and several phones.** With 20 windy nights a mid-rise first mode is found from
30-minute sessions; on typical nights it takes 20 sessions of 8 hours to reach 88%. Coherent
processing of synchronised phones gives about 2, 3 and 4 times the detection score of incoherent
stacking for 2, 4 and 8 phones, is insensitive to clock errors up to 200 ms, and recovers first-mode
shape amplitudes to about 2% RMS when the mode is well above the limit. On typical nights it does not
rescue a mode that single phones cannot see.

**False alarms on pure noise.** 1.25% of building stacks at a detection score of 6, none in 400 at 7.

**Artefact rejection (Milestone 4).** On a held-out set of 48 buildings and 432 time-domain sessions with HVAC tones, elevator rumble, appliances, mains aliases, footsteps, soft surfaces and a phone model with its own resonance, 76.9% of raw candidate peaks are non-structural. After rejection the share is 9.8% of all accepted peaks and 3.5% of the modes the product would publish (2 of 57; lowest three accepted modes per building). The reported fundamental is a true first mode in 34 of 36 buildings. Cost: 31% of genuine structural candidates are rejected and 12 of 48 buildings get no fundamental. The most effective tests were peak width and vertical motion. Thresholds were tuned on a separate simulated set; they are not tuned on real interference.

**Vulnerability model (Milestone 5).** Hazus 6.1 class parameters (`REF`) with a capacity spectrum
method reproduce the expected class ordering. A measured period narrows the score band from a median
of 15.7 to 8.9 points and moves the score by a median of 2.9 points. A soft first storey is detected
from mode shapes in all trials on windy nights with 3 to 5 synchronised phones, and in 35 to 100% of
trials on typical nights.

**Change detection (Milestone 6).** One year of sessions in five-night epochs, frequency following temperature and an unobserved slow term, a permanent stiffness loss half-way through, threshold set for 5% false alarms. Smallest loss detected in at least 90% of trials: 9 storeys with an 80 ug phone: not reached with 40 sessions, not reached with 60 sessions, 2.5% with 100 sessions, 5% with 200 sessions. 9 storeys with a 150 ug phone: not reached with 40 sessions, not reached with 60 sessions, not reached with 100 sessions, not reached with 200 sessions. 25 storeys with an 80 ug phone: not reached with 40 sessions, not reached with 60 sessions, 5% with 100 sessions, 5% with 200 sessions. Each cell has 30 trials, so rates carry roughly 9 points of sampling error; read the 80 ug results as 5% with 100 or more sessions a year. Residual scatter after temperature correction is 0.63% to 1.39% of frequency. Step sizes are recovered without bias. The first version of this experiment failed (a 20% loss was caught in only 20 to 60% of trials) because per-epoch peak detection sometimes latched onto the other horizontal mode; tracking now registers each epoch against reference modes, using all peaks jointly. The environmental terms are assumptions at the mild end of the published range, so real detection limits will be worse.

**Demo city (Milestone 7).** 687 real OpenStreetMap footprints in downtown San Francisco with simulated structures, contributors and 30404 sessions (one phone per 1500 m2 of floor area, assumed). 222 buildings scored, 255 need more data, 210 have none. Scored by height: 7 of 231 (1-3 storeys), 21 of 180 (4-7), 63 of 134 (8-14), 76 of 86 (15-29), 55 of 56 (30+). First-mode frequency within 5% of the simulated truth in 94% of scored buildings; wrong mode reported as the fundamental in 13. Stiffness anomalies: 25 planted, 8 scored, 2 flagged. Frequency-drop alerts: 4 of 4 damaged buildings caught, 1 false alert. API, portfolio upload and dashboard run locally against this data (39 service tests pass); nothing is deployed.

**Tooling for the real-building test.** `experiments/m3_validate_real.py` reads uploaded session
files and prints the comparison table. A dress rehearsal with simulated stand-ins for the ten
reference buildings ran end to end through the upload codec (`results/m3_rehearsal_sim.md`). That
rehearsal shows the tooling works; it is not evidence about real buildings.

## 3. What failed, is weak, or was not done

**Not done.**

- The Android app has never been compiled or run. The Kotlin DSP was checked only through a Python
  port of the same streaming algorithm against exported test vectors. Expect compile errors.
- No overnight sessions, no battery measurement, no noise-floor measurement, no real building.
- The iOS app is a skeleton.
- The score was not validated against earthquake damage. No open dataset pairs pre-event modal
  measurements with post-event damage for the same buildings. A class-level comparison with the
  ACI 133 Turkey 2023 database was identified but not run.
- Nothing is deployed. The PostGIS schema was written but never executed; local storage is SQLite.
  The H3 library has no build for the Python version used, so the spatial index runs on a fallback
  grid and the H3 path is untested.
- The hold-and-notify step before a high-risk anomaly reaches a buyer is designed
  (`docs/responsible_use.md`) but not implemented in the API.

**Weak results.**

- The stiffness-anomaly detector is close to useless with height as the only covariate: a building
  30% softer than expected is flagged 4% of the time, 50% softer 12%, 75% softer 50%. "This building
  is 30% softer than its class" cannot be said with confidence from height and class alone.
- The score itself moves only 3 to 6 points when stiffness halves. Most of a measurement's effect
  comes through the class it implies, and that class model is a small illustrative table.
- Low- and mid-rise buildings on ordinary nights are below the detection limit for most phones under
  the assumed excitation.
- Damping is a soft output and stays one.

**Things that broke along the way and what they taught.**

- The first fit model failed at very high signal-to-noise for closely spaced modes, and two first
  modes within about 14% of each other merged into one broad peak until a split test was added.
  Symmetric buildings whose two directions are within a few percent will still be reported as one
  mode with inflated damping.
- The detector tripped on the anti-alias filter's roll-off at band edges. Only the comparison between
  the time-domain and fast simulators exposed it.
- A "present in most sessions" test rejected real wind-driven modes, because they really are far
  stronger on windy nights. It was replaced by a single-session test.
- The pipeline picked a second mode as the fundamental in 6 of 15 buildings in the first demo run. A
  mode-order check now refuses to score in that situation.
- A test that compared phone models inside one building confused quiet phones with artefacts and had
  to be weakened; the fleet-wide check carries that job.
- Raw bootstrap intervals were too narrow (67 to 74% coverage at nominal 90%) and had to be corrected.

## 4. Three next steps to a paid pilot

1. **Get the first real night, this month.** Compile the Android app (JDK and Android SDK needed),
   fix what does not build, and run the two cheapest decisive measurements from
   `docs/validation_protocol.md`: each available phone model overnight on a ground-floor slab for its
   noise floor, and the same phones overnight on an upper floor of one tall and one mid-rise
   building. These two numbers replace the two largest assumptions in every table above and say
   within a week whether mid-rise coverage is realistic.
2. **Validate on five reference buildings and publish the table.** Use buildings with published
   ambient values across 3 to 30+ storeys, starting with the tall ones where the method is most
   likely to work. `experiments/m3_validate_real.py` produces the table. Label thresholds for
   artefact rejection on those sessions at the same time. A buyer will ask for this table before
   anything else.
3. **Run the pilot around what a buyer already knows.** Approach a reinsurer or a commercial property
   insurer with a portfolio of mid- and high-rise buildings where structural systems are documented.
   Their engineering data fixes the weak class model, their policyholder channel supplies phones in
   the same buildings, and the pilot question is narrow and falsifiable: does a measured period, added
   to their existing class and height, change their vulnerability estimate enough to pay for? Settle
   the data-licence questions in `docs/licences.md` (OpenStreetMap share-alike, GEM non-commercial
   terms) before any data changes hands.
