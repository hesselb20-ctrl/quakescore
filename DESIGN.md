# QuakeScore design

QuakeScore estimates each building's natural frequencies, damping and (where coverage allows) mode
shapes from ambient vibration recorded by phones lying still inside it, and turns those measurements
into a per-building seismic vulnerability score with stated uncertainty.

It is a statistical screening layer. It is not a structural engineering assessment.

Status labels used everywhere in this repository:

| Label | Meaning |
|---|---|
| `REAL` | Measured on a real building with a real phone |
| `SIM` | Produced by the simulator in `quakescore/sim` |
| `REF` | Taken from a cited publication |
| `ASSUMED` | An engineering assumption that has not been measured yet |

No result may be reported without one of these labels. The dashboard, API and pitch pack carry the
label through as a `provenance` field.

## 1. What we build on

The MyShake group at UC Berkeley showed that phones can recover building natural frequencies and
damping from ambient vibration, validated on shake tables and on Millikan Library. The verified
citation list, with what each paper did and did not show, is in `docs/references.md`. We reuse the
finding that it is possible, and the stated limits: phone self-noise dominates at low frequency,
short stiff buildings need stronger excitation, and output-only identification degrades without time
sync and orientation alignment. We do not re-derive those results. The work here is the part that
does not exist yet: a fleet pipeline that stacks many weak sessions per building, rejects
non-structural peaks at scale, attaches uncertainty, and maps the result to fragility.

## 2. The physical problem, with numbers

A lightly damped mode with RMS acceleration `sigma`, frequency `f` and damping ratio `zeta`, driven
by broadband forcing, has a one-sided peak power spectral density of

    S_peak = sigma^2 / (pi * zeta * f)

A mid-rise roof moving at 15 ug RMS at 1.5 Hz with 1.5% damping therefore peaks at about
56 ug/sqrt(Hz). A phone accelerometer has a noise density of roughly 70-300 ug/sqrt(Hz). The
structural peak is at or below the sensor noise floor in a single spectrum, often by a factor of
3-30 in power, and lower floors are worse because amplitude follows the mode shape.

The peak is still recoverable because sensor noise is broadband and smooth while the mode is a narrow
bump of known shape. Averaging `K` spectral windows shrinks the scatter of the estimate as
`1/sqrt(K)`, and a matched filter over the `n` bins under the peak gains another `sqrt(n)`. A bump
with peak-to-floor power ratio `r` is detectable at about 5 sigma when

    r * sqrt(K * n_eff) >~ 5

That inequality is the whole business case in one line: detection is bought with record length,
quiet hours, number of sessions, number of phones, and (with time sync) coherence between phones,
whose cross-spectra are free of sensor-noise bias. The simulator exists to turn this into a measured
detection-limit table per building height before any claim is made (Milestone 1).

## 3. Signal chain

```
phone accelerometer (100-500 Hz, 3 axes, sensor timestamps)
  -> stationarity / flat / quiet gate            (device)
  -> UTC-anchored uniform resampling             (device)
  -> privacy low-pass + decimation to 50 Hz      (device)   nothing above 25 Hz survives
  -> gravity estimate, rotate to level frame     (device)
  -> three zoom bands, 2048-point Hann windows   (device)
  -> per-window 3x3 cross-spectral matrix
     accumulate sum(G), sum(|X|^4), count        (device)
  -> upload: features + building id + floor + sync quality
  -> per-building stacking across sessions/phones (server)
  -> peak detection, artefact rejection           (server)
  -> modal identification + bootstrap             (server)
  -> class, stiffness anomaly, fragility, score   (server)
  -> change detection over time                   (server)
  -> API, exports, dashboard
```

### 3.1 On-device feature specification (the contract)

The Python reference implementation is `quakescore/device/pipeline.py`. The Kotlin implementation in
`android/dsp-core` must reproduce it to within float32 rounding; test vectors are exported from
Python (`tests/vectors`).

1. **Sampling.** Request 200 Hz from `TYPE_ACCELEROMETER` (uncalibrated variant where available).
   Keep sensor event timestamps. Measure the true rate; it is rarely the nominal one.
2. **Time base.** Map sensor timestamps to UTC with the best available source (GNSS time, else NTP),
   sampled at session start, every 10 minutes and at session end, and fit offset and drift linearly.
   Record source, residual and estimated uncertainty in milliseconds.
3. **Uniform grid.** Linearly interpolate each axis onto a uniform grid at `fs_g` = 200 Hz (100 Hz if
   the device cannot deliver at least 190 Hz). Grid instants are integer multiples of `1/fs_g` since
   the Unix epoch, so every phone uses the same grid. The interpolation droop `sinc^2(f/fs_raw)` is
   corrected on the server using the reported raw rate.
4. **Privacy filter and decimation.** Linear-phase FIR low-pass (pass 20 Hz, stop 25 Hz, at least
   80 dB) and decimate to 50 Hz, with decimation phase anchored to the epoch grid. This filter is a
   privacy guarantee, not just anti-aliasing: speech fundamentals start near 85 Hz and no content
   above 25 Hz exists in any stored or uploaded quantity. Raw samples are held in RAM only and are
   never written to disk.
5. **Zoom bands.** Two further divide-by-4 stages with the same normalised filter give three bands:

   | Band | Rate (Hz) | Window (s) | Resolution (Hz) | Home range (Hz) |
   |---|---|---|---|---|
   | H | 50 | 40.96 | 0.0244 | 5 - 20 |
   | M | 12.5 | 163.84 | 0.0061 | 1.25 - 5 |
   | L | 3.125 | 655.36 | 0.0015 | 0.1 - 1.25 |

   Each band uses 2048-point Hann windows with 50% overlap, window `k` starting at band sample
   `1024*k` counted from the epoch. Relative resolution is at most 0.5% of frequency inside each home
   range, so a mode with 1% damping spans at least four bins across its half-power width.
6. **Gating.** Per one-second block: peak-to-peak and RMS on each axis, and tilt of the running
   gravity estimate. A second is flagged when it exceeds a multiple of the session's running median
   (default 5x RMS) or tilt moves more than 0.2 degrees. A window containing a flagged second is
   dropped. A session only starts when the phone has been flat (within 15 degrees), still and
   screen-off for 2 minutes; by default only while charging.
7. **Levelling.** Gravity is the session mean of accepted samples. Samples are rotated so `z` is
   vertical. Yaw is left arbitrary; the server works with rotation-invariant quantities.
8. **Accumulators per band.** For accepted windows: the sum of the one-sided 3x3 Hermitian
   cross-spectral matrix `G_ij(f) = X_i(f) conj(X_j(f))` in (m/s^2)^2/Hz, the per-axis sum of
   `|X_i|^4` (for the tone test in section 5), and the window count `K`.
9. **Sync frames (opt-in tier B).** For bands L and M, the complex window spectra restricted to
   server-hinted frequency ranges around candidate modes, so the server can form cross-spectra
   between phones in the same building. Band-limited below 5 Hz.
10. **Upload.** One compressed message per session: random session id, building id, floor estimate
    and its method, start/end time rounded to the minute, sync quality, device model and sensor
    name, measured rate and resolution, accepted window counts, the accumulators, five-band noise
    summary, battery temperature, and battery level at start and end.

### 3.2 Building matching and floor

Location is used once, on the device, at session setup. The app takes a fix, rounds it to 0.01 degrees
(about 1 km) and asks the server for the building footprints around that rounded point. The server
answers and does not store or log the coordinates. The app snaps the precise fix to the nearest
footprint on the device and asks the user to confirm. Only the building id is uploaded with a
session. Footprints come from OpenStreetMap or Overture. (An H3 resolution-8 cell would serve the
same purpose; the rounded point avoids shipping a native library in the app.)

Floor is estimated from the barometer in this order: pressure change between arrival at the building
entrance (ground level) and the resting position; pressure against a ground-floor reference phone in
the same building; pressure against a weather-station reference with a learned per-device bias;
manual entry. Each method is stored with the estimate because their errors differ by an order of
magnitude.

### 3.3 Two platforms

Android can run the gate in a foreground service and record whenever the phone is charging, flat and
still. iOS does not allow unattended background accelerometer access, so iOS ships "measure now":
the user starts a 30-60 minute session, typically at bedtime on a charger, with the app in the
foreground and the screen dimmed. The spectral contract is identical. Differences are documented in
`docs/platforms.md`.

## 4. Simulator (built first)

`quakescore/sim` contains:

- **Building.** Lumped-mass shear buildings, 1-40 storeys, two horizontal directions and a torsional
  chain, storey stiffness tuned so the fundamental period follows a period-height relation with
  class scatter, modal damping 1-5%. Response is computed by modal superposition in the frequency
  domain, which is exact for a linear system under stationary forcing.
- **Excitation.** Ground microtremor (base acceleration with a prescribed PSD level: quiet, typical
  urban night, busy) and wind (per-floor drag fluctuation with a von Karman spectrum, power-law
  profile, vertical coherence and aerodynamic admittance). Excitation levels are scenario parameters
  because they are the largest unknown; results are also reported against roof RMS acceleration,
  which is the physically meaningful axis.
- **Phone.** Per-model noise density with a low-frequency corner, quantisation to the device LSB,
  non-nominal sample rate, timestamp jitter, clock drift and residual sync error, arbitrary yaw and
  small tilt, and furniture coupling as a single-degree-of-freedom transmissibility (a soft mount
  amplifies near its resonance and attenuates above it).
- **Interference.** HVAC and pump tones, elevator runs, washing-machine spin sweeps, mains-related
  aliases, footstep transients, and phone-model resonances that appear in every building for a given
  model.

A second, fast path draws session spectra directly from their sampling distribution given the
analytic PSD. It is validated against the time-domain path and used only for large sweeps and the
demo city; every table states which path produced it.

## 5. Identification

Stacking. For each building and band, sessions are combined with inverse-variance weights
`w = K / B^2`, where `B` is the session's median noise level in the band. The yaw-free stacking
statistic is the horizontal trace `T(f) = G_xx + G_yy`. Sensor noise appears in `T` as a smooth
baseline that is fitted, not assumed.

Candidate detection. The stacked spectrum is divided by a robust baseline (running median in
log-frequency). A matched filter scans a grid of frequency and damping with the single-mode
acceleration-response shape and reports candidates above a z-score threshold, with the noise scale
taken from the measured scatter of the whitened spectrum.

Estimators, all implemented and compared on the simulator:

| Method | Input | Role |
|---|---|---|
| FDD (peak of first singular value) | stacked CSD | frequency, mode shape; baseline method |
| EFDD | SDOF bell around the peak, inverse FFT, log decrement | frequency and damping at good SNR |
| SSI-COV | correlation functions from the stacked spectra | frequency and damping, stabilisation check |
| Random decrement | band-passed time series on device | damping cross-check at good SNR |
| Spectral curve fit | stacked trace near each candidate | frequency and damping at low SNR |

The choice of production estimator per SNR regime is made from simulator error tables, not in
advance (results in `results/m1_*.md`).

Mode shapes need simultaneous recordings on several floors. With tier B sync frames, the server
forms the cross-spectral matrix across phones and takes the first singular vector at the modal
frequency. Each phone contributes a two-component horizontal vector, so unknown yaw is absorbed
without a compass. Without sync frames only frequency and damping are reported.

Uncertainty. Every reported parameter carries a bootstrap interval obtained by resampling sessions
with replacement and repeating stacking and estimation. Buildings with fewer than the minimum
number of sessions or contributors are not reported at all.

Artefact rejection (Milestone 4). A candidate is kept only if it passes all of:

1. **Width.** Fitted damping between 0.3% and 8%. Machinery tones are narrower than any structure;
   furniture resonances are broader.
2. **Tone and burst.** Normalised periodogram variance per bin. A Gaussian random response gives 1; a
   steady sinusoid tends to 0; energy that arrives in bursts (elevator runs) gives well above 1.
3. **Vertical.** A lateral building mode has no vertical motion. A peak that is also present on the
   vertical axis is floor-borne machinery.
4. **Support and single session.** The pooled per-session amplitude at the peak must be positive and
   significant, and the peak must not live in one night only. (A test that required similar strength
   in most sessions was tried and dropped: wind-driven modes really are far stronger on windy nights.)
5. **Fleet check.** Not at a frequency that the same phone model reports across many unrelated
   buildings.
6. **Detection strength.** Score of at least 7, or 6 when two contributors see the peak independently.
7. **Plausibility window and mode order.** The fundamental must lie within a wide factor of the
   period expected for the building's height, and the pipeline refuses to score when the lowest
   identified peak may be a second mode. The window is wide on purpose so that anomalously soft
   buildings are not discarded.

The false-positive rate is measured on a labelled set of contaminated simulated sessions, and later
on labelled real sessions.

## 6. Vulnerability mapping

Inputs: measured fundamental period per direction, damping, mode shape where available, and free
public attributes (height or storeys, footprint, age, material and use tags).

1. **Structural class.** A prior over HAZUS model building types from height, age, tags and a
   regional mix table, updated by the likelihood of the measured period under each class's
   period-height relation (lognormal scatter). The class is reported as a distribution and mapped to
   a GEM taxonomy string.
2. **Stiffness anomaly.** `k_ratio = (T_expected / T_measured)^2` under the most probable class,
   with a z-score against class scatter. "30% softer than expected" is `k_ratio = 0.7`. A flag is
   raised only when the building is anomalous under every plausible class, because class ambiguity
   and stiffness anomaly are otherwise indistinguishable.
3. **Fragility adjustment.** Start from the class's HAZUS capacity curve and structural fragility.
   Scale the elastic period by `T_measured / T_expected`; keep class strength; scale damage-state
   median displacements by height and, where a mode shape exists, by the ratio of class to measured
   drift concentration (a soft storey concentrates drift and lowers the roof displacement at which
   the critical storey fails). Elastic damping uses the measured value when its interval is tight
   enough, otherwise the class value.
4. **Demand and damage.** For standard scenarios (PGA 0.15, 0.30 and 0.60 g on a standard spectral
   shape) the capacity spectrum method gives the performance point, and the fragility gives
   probabilities of slight, moderate, extensive and complete damage.
5. **QuakeScore.** `100 * (1 - weighted mean damage ratio)` over the scenarios, so 100 is the least
   vulnerable. The band is the 5-95% interval from propagating measurement bootstrap samples and
   class probabilities. A score is never shown without its band and its provenance label.

What this is not: the fragility adjustment is physics-based and has not been calibrated against
observed damage. Section 9 states what validation is possible.

## 7. Change detection

Per-building frequency series (one estimate per stacking period) are regressed on outdoor
temperature, annual harmonics and session vibration amplitude. A sustained shift in the residual is
tested with a two-sided CUSUM and reported with its size, onset and false-alarm rate. The synthetic
damage test reduces simulated stiffness by 5, 10 and 20% (frequency drops of 2.5, 5.1 and 10.6%) and
reports the minimum detectable change against the number of sessions.

## 8. Privacy architecture

- Opt-in with a plain-language screen listing exactly what leaves the phone.
- No audio. No content above 25 Hz. No raw samples on disk or on the wire.
- Location is used on the device to pick a building. The only position that leaves the phone is a
  point rounded to about 1 km in the footprint request, which the server does not store; sessions
  carry the building id only. No trajectories exist to store.
- Session ids are random and not linked to an account. A contributor pseudonym, salted per building,
  is used only to count distinct contributors.
- Session times are rounded to the minute and published only as building-level aggregates.
- K-threshold: building outputs are released only when at least `K_c` distinct contributors and
  `K_s` sessions are combined (defaults 3 and 5), so one household's presence or routine cannot be
  inferred. Sub-threshold buildings appear in the coverage map as "needs data" without parameters.
- Responsible use: scores are risk information, shown with uncertainty; high-risk anomalies trigger
  a notice and an inspection route for owners and residents before the score is released to buyers
  (`docs/responsible_use.md`). GDPR roles, lawful basis, retention and deletion are in
  `docs/privacy.md`.

## 9. Validation plan

| Question | Evidence | Label |
|---|---|---|
| Does the pipeline recover known parameters? | Simulator sweeps, error against truth | SIM |
| What is the detection limit by height? | Simulator table over height, noise, excitation, sessions, phones | SIM |
| Does it work on real buildings? | 5+ buildings, 3 to 30+ storeys, against published values | REAL (needs phones in buildings) |
| Are non-structural peaks rejected? | Labelled contaminated sessions | SIM first, REAL later |
| Is the score meaningful? | Sensitivity and consistency checks; comparison with reconnaissance damage data by class; expert ratings on a test set | partly possible |
| Can stiffness loss be detected? | Synthetic damage test | SIM |

Limits stated up front. Modal parameters can be validated properly against instrumented buildings.
The score cannot be validated building-by-building against damage, because buildings with both a
pre-event modal measurement and a post-event damage grade barely exist. What can be done is
class-level comparison against reconnaissance datasets and comparison against engineers' ratings.
Until then the score's validity rests on the published fragility framework it inherits.

## 10. Stack

Python (NumPy, SciPy) for simulator, identification and models. Kotlin for Android. FastAPI for the
service; Postgres with PostGIS and H3 in production, SQLite for local development. Static dashboard
with MapLibre GL and OSM tiles. All dependencies are MIT, BSD or Apache licensed. Data licences
(ODbL for OSM, and the terms of any fragility or damage dataset) are tracked in `docs/licences.md`.

## 11. Repository layout

```
quakescore/sim        building, excitation, phone, interference, fast spectral path
quakescore/device     reference on-device pipeline (mirrored by android/dsp-core)
quakescore/ident      stacking, detection, FDD, EFDD, SSI-COV, random decrement, curve fit, bootstrap
quakescore/artefacts  non-structural peak rejection
quakescore/vuln       class model, period relations, capacity spectrum, fragility, score
quakescore/change     drift tracking and change detection
quakescore/service    API, storage, portfolio matching, coverage engine
experiments           one script per milestone, writing to results/
results               measured tables (JSON and Markdown), each with a provenance label
android, ios          collector apps
dashboard             static demo site
docs                  references, privacy, platforms, validation protocol, pitch pack
tests                 unit and regression tests, device test vectors
```
