# Field validation protocol

Two milestones need physical phones in buildings and have not been run:

- **M2**: collector app field test (battery cost, noise floor per phone model).
- **M3**: real-building validation against published or reference modal values.

Until they are run, no result in this repository is labelled `REAL`. Reference values quoted here are
`REF` and come from `docs/references.md`. Numbers marked ASSUMED are proposals to be revised after the
simulator detection-limit table (Milestone 1).

**Rule: nothing is labelled `REAL` until it comes from this protocol**, with the raw session records,
the phone model, the building, the date and the reference value kept with it.

## Part A. M2: collector app field test

### A1. Goals

1. Show the app records unattended overnight, on several phone models, without user action beyond
   placing the phone.
2. Measure battery cost per session against the target: under 3 percent per session, stretch under
   1 percent.
3. Measure the noise floor of each phone model. This also settles the open question in
   `docs/references.md` section (b): the roughly 20 dB gap between datasheet noise densities and the
   published phone noise floor.

### A2. Overnight sessions

- At least 20 overnight sessions in total, across at least 3 phone models (ASSUMED) and at least 2
  buildings. Count only sessions that completed.
- Conditions: phone flat on a hard surface, screen off, charging (default), session started by the
  app's own gate (flat within 15 degrees, still, screen off for 2 minutes).
- Record every session regardless of outcome. Failed sessions are data.

### A3. Battery cost per session

| Step | Detail |
|---|---|
| Start | Battery percent at the moment the session starts (the app logs it), charging state, screen state, battery temperature |
| End | Battery percent at session end, charging state, battery temperature |
| Charging | Record whether the charger was connected throughout. If charging, percent change understates the draw, so charged runs are for functionality only |
| Battery-cost runs | Run on battery, not charging, screen off, for a fixed duration (for example the length of a normal session). Cost = percent at start minus percent at end |
| Control run | Same phone, same duration, airplane mode on, app idle (not recording). Subtract it. Repeat the control on each model |
| Second control | Same, with the app recording but without upload, to separate sensing from network cost |
| Repeats | At least 3 battery-cost runs per model (ASSUMED) to see run-to-run spread |
| Report | Net cost per session in percent and, where logged, per hour; per model; with the spread |

Targets: net cost under 3 percent per session; stretch under 1 percent. Battery percent is coarse
(whole percent). If the cost is near 1 percent, extend the run and report cost per hour as well.

### A4. Noise floor per phone model

- Phone on a concrete ground-floor slab, isolated from desks and walls, no one moving nearby, no
  machinery on the floor (a basement would be better still; Kong 2016 used a quiet Berkeley basement).
- Overnight, screen off, same app and sampling settings as field use (200 Hz request, raw rate logged).
- At least one night per model. Place two units of the same model where possible, to separate unit
  variation from model variation (ASSUMED).
- Output: noise PSD per axis, in ug/sqrt(Hz) and in dB re 1 (m/s^2)^2/Hz (state both), across the
  bands used by the pipeline (0.1-20 Hz). Compare with the datasheet value for the model's sensor
  and with the -75 and -70 dB figures of Patel 2023 and Kumar 2025. Report the gap in dB.
- Output feeds the simulator's per-model noise parameters, replacing the ASSUMED values.

### A5. What to log

Per session: app version, phone model, sensor name and vendor, OS version, measured sample rate,
timestamp jitter, time-sync source and residual, session start and end, battery percent and
temperature at start and end, charging state, number of accepted and rejected windows with rejection
reasons, window counts per band, five-band noise summary, floor estimate and method, upload success,
bytes sent, app crashes. For the noise-floor and battery runs also note room, surface, and whether
anyone was in the room. Per night: weather (wind, rain, outdoor temperature) from a public source.

### A6. Pass conditions for M2

- At least 20 completed overnight sessions logged.
- Battery cost reported for every model tested, with control subtracted. Target and stretch stated as
  met or not met.
- Noise floor reported for every model tested, and the dB gap to the published figure stated.
- All raw logs kept. Nothing from M2 is described as a building measurement.

## Part B. M3: real-building validation

### B1. Goal

Show on at least 5 real buildings of different heights, from 3 to 30 or more storeys, that the
pipeline's first-mode frequency agrees with a published or reference value, and report the detection
limit by height with real data.

### B2. Candidate buildings

From the ground-truth table in `docs/references.md` section (c). **Access permission from the owner or
manager is needed for every building**, including permission to leave a phone overnight and to use
barometer-based floor estimation. Availability and access have not been checked for any building.

| Candidate | Storeys | Height | Published f1 (Hz) | Type of published value | Height class | Notes |
|---|---|---|---|---|---|---|
| Broad Center, Pasadena CA | 3 | NOT VERIFIED | EW 2.67, NS 2.43 | amb, 2003, preliminary | **Low-rise** | Stiff braced steel frame. Seasonal range 4.9 to 6.5 percent (Clinton 2006) |
| Albina Yard, Portland OR | 4 | 15.39 m | NS 2.86, EW 4.20 | amb, Jan 2017, about 2 h | **Low-rise** | Mass timber. Damping method spread 1.38 vs 5.66 percent |
| Millikan Library, Pasadena CA | 9 | 43.9 m | amb EW 1.19, NS 1.72 | amb 2002-2004 mean | Mid-rise | Permanent reference sensor on the 9th floor (station CI MIK); data access to be arranged. Partitions added 2004 raised EW f1 about 4 percent |
| 9-storey dwelling, Grenoble | 9 | NOT VERIFIED | T 2.28, L 2.73 | amb | Mid-rise | 1939 RC; year of test NOT VERIFIED |
| Grenoble City Hall | 13 | 52 m | L 1.162, T 1.224 | amb, one-year mean | Mid-rise | Long record available in the literature |
| Ophite Tower, Lourdes | 18 | about 59 m (derived) | L 1.74, T 1.73 | amb, one year | High-rise | |
| UCLA Factor Building, Los Angeles | 17 | NOT VERIFIED | NS 0.58-0.60, EW 0.54-0.56 | amb, 2002-2003 | High-rise | Instrumented building |
| Pacific Park Plaza, Emeryville CA | 30 | 95 m | 0.48 (range 0.48-0.54) | amb, second-hand | Tall | Same building used by Kumar 2025 with phones: 0.47 Hz |
| Belledonne / Mont-Blanc, Grenoble | 30 | 100 m | T 0.67 / 0.65; L 0.89 / 0.84 | amb, one month | Tall | |
| Millennium Tower, San Francisco | 58 | 197 m | 0.26, 0.30 | amb, 2024, phones and Episensor | Tall | Floor count 58 vs 56 inconsistent in source |

Proposed first set of five, spanning heights: **Broad Center (3), Albina Yard (4), Millikan (9),
Grenoble City Hall or Factor (13-17), Pacific Park Plaza (30).** Substitute freely depending on access;
keep at least two low-rise, one mid-rise and one 30-plus.

Expect the low-rise buildings to be the hard cases. The only ambient phone study found (Kumar 2025,
54-197 m) reports many short-building recordings rejected for low SNR. A failure to detect a mode in
a low-rise building is a detection-limit result and is reported as such, not hidden.

### B3. Phone placement

- Upper third of the building, on a hard surface (floor, desk top), flat, away from machinery,
  lifts, HVAC, stairwells with heavy use and external doors.
- Where possible, phones on several floors at the same time, to give mode shape data. Note the floor
  of every phone.
- Record the floor number as observed on site as well as the barometer estimate, to test the floor
  method.
- Phone screen off, charging, in a position that will not be disturbed. Leave a note for staff.
- Record the exact position (room, distance from the core and from the building corner, surface,
  orientation of the phone x axis relative to the building axes) in the session sheet.
- If a reference sensor is on the same floor, place phones within a metre of it.

### B4. Number of nights

At least 7 nights per building (ASSUMED), including at least one windy night if possible, to build up
stacked sessions. Report results against the number of nights and sessions, so the detection limit by
sessions is visible. Revise the number after the simulator table says how many sessions a given height
needs.

### B5. Reference measurement

- If a reference accelerometer can be borrowed, place it beside the phones for the same nights. The
  prior art used a permanent Episensor (Kong 2018, Kumar 2025) and TE Connectivity 3022 sensors (Patel
  2023) as references. Use whatever is available and record its model, range and noise.
- Where none can be borrowed, the reference is the published value from `docs/references.md`, which
  is a weaker comparison (see B7).
- Use the same time base, so phone and reference records can be compared in the same windows.

### B6. Comparison metric

For each building and each direction, first-mode frequency error against the reference:

    error = (f_phone - f_ref) / f_ref

- **Minimum target: absolute error within 10 percent.**
- **Stretch target: within 5 percent.**
- Report the signed error, the absolute error and the bootstrap interval of f_phone.
- Report a miss (no mode detected, or a non-structural peak accepted) as a result, with the reason.
- Report the number of sessions and nights needed before the estimate stabilised.

### B7. Caveat on published reference values

Published values come from different amplitude levels, years and conditions than our measurements. A
few percent of real difference is expected and is not an error of the method. Evidence from
`docs/references.md` section (e):

- Millikan: daily temperature swing of at least 1 percent, long-term range 5.1 percent (EW) and
  partitions added in 2004 raised EW f1 about 4 percent.
- Broad Center: 6.5 percent seasonal range in EW.
- Factor Building: earthquake-level f1 about 12 percent lower than ambient.
- Rain and wind: about 3 percent shifts.

So a phone-versus-published error under about 5 percent can be fully explained by real change. A
co-located reference measured on the same nights removes most of this and is much preferred. State in
every result which kind of reference was used.

### B8. How damping is reported

Damping is reported with an interval, **not as a pass or fail**. Each estimate gives the value, the
estimator used, the bootstrap interval and the number of sessions. Comparisons with published values
are shown as a table with both numbers, not a verdict. Published damping is itself spread by method
(Albina Yard 1.38 vs 5.66 percent from two estimators) and over time (damping scatter 9-14 percent
coefficient of variation in Mikael 2013), so agreement is judged by whether intervals overlap, and by
whether the value lies in the range seen in the literature (about 0.6 to 1.1 percent for tall
ambient cases in `docs/references.md` section h).

### B9. Results table template

One row per building and direction. Leave empty until measured. Provenance for every filled cell is
`REAL`, except the reference columns, which are `REF` unless a co-located reference was measured.

| Building | Storeys | Height (m) | Phone model(s) | Phone floor(s) | Nights | Sessions used | f_ref (Hz) | Ref type (published / co-located) | f_phone (Hz) | Interval | Error (%) | Within 10% | Within 5% | zeta (%) | zeta interval | Mode detected | Notes | Label |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| | | | | | | | | | | | | | | | | | | |
| | | | | | | | | | | | | | | | | | | |
| | | | | | | | | | | | | | | | | | | |
| | | | | | | | | | | | | | | | | | | |
| | | | | | | | | | | | | | | | | | | |

### B10. Pass conditions for M3

- At least 5 buildings, covering 3 to 30 or more storeys, with owner permission documented.
- At least one reference value per direction measured or cited, with its type stated.
- Every building reported: successes, misses and rejected recordings.
- The share of buildings within the minimum and stretch targets stated as counts, not as a claim of
  validation beyond those buildings.
- Results written to `results/` with the label `REAL`, raw records retained, and the table above
  filled.

## Part C. Safety, consent and data handling

- Owner or manager permission in writing for each building; no phone left in a space without it.
- Phones used for field work run the same app as the product and follow `docs/privacy.md`: no audio,
  nothing above 25 Hz, no raw samples stored.
- Field sheets (placement, floors, names of contacts) are kept apart from session data and not
  published.
- Occupants are told what the phone is doing when it is placed in a shared space.
- If a building shows an anomalous result, the rules in `docs/responsible_use.md` apply; no result
  from M3 is reported to any outside party as a building assessment.
