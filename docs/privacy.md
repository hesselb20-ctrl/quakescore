# Privacy and data protection design

This document describes how QuakeScore is designed to limit what it learns about people. It does not
claim legal compliance. A lawyer must review it for each launch country (section 9). Anything marked
PROPOSED is a design choice not yet fixed in `DESIGN.md`. The collection contract is in `DESIGN.md`
sections 3.1 and 8.

## 1. What we collect and what we never collect

Collected, per session, from a phone lying still in a building overnight:

- Spectral accumulators for horizontal and vertical acceleration below 25 Hz (sums of cross-spectral
  matrices and window counts), not waveforms.
- The building id, a floor estimate and the method used, session start and end rounded to the minute.
- Device model, sensor name, measured sample rate, accepted window counts, a five-band noise summary,
  battery temperature, battery level at start and end, time-sync quality.
- A random session id and a contributor pseudonym salted per building.

Never collected:

| Never | How the design enforces it |
|---|---|
| Audio | The app never opens the microphone. No audio permission is requested |
| Content above 25 Hz | A linear-phase low-pass (pass 20 Hz, stop 25 Hz, at least 80 dB) runs before anything is stored or sent |
| Raw samples on disk or on the wire | Raw samples are held in RAM only and discarded after the accumulators are updated |
| Location uploads | Location is used once, on the device, at session setup to pick a building. The footprint request sends a point rounded to 0.01 degrees (about 1 km), which the server does not store; sessions carry the building id only. No trajectories exist |
| Account identity | Session ids are random and not linked to an account. No name, email or phone number is needed to contribute |
| Contacts, photos, other sensors' content | Not requested. The barometer is read only to estimate floor |

Opt-in is explicit, with a plain-language screen listing exactly what leaves the phone.

## 2. Why the 25 Hz low-pass is a privacy guarantee

Speech fundamental frequencies start near 85 Hz (`DESIGN.md` section 3.1). Nothing above 25 Hz exists
in any stored or uploaded quantity, so the fundamental of a human voice is outside the retained band
by more than a factor of three, with at least 80 dB of attenuation.

This is stated as a **design guarantee**, not as an empirically proven one. Aliasing or non-linear
effects in the sensor chain could in principle fold some higher-frequency energy into the retained
band before the filter. To prove the guarantee, the following must be tested and the results recorded
in `results/`:

1. **Speech recovery.** Play speech near a phone (various distances, loudness, surfaces, including the
   same table), record through the full on-device pipeline, and attempt recovery with speech
   recognition and speaker identification on the retained band and on the uploaded accumulators.
   Expected result: nothing above chance.
2. **Aliasing.** Inject tones from 25 Hz up to the raw Nyquist frequency and measure the leakage into
   the retained band at the filter's stated rejection. Repeat across several device models, since
   sensor-side anti-aliasing varies.
3. **Keystroke and tap information.** Record typing and tapping on the same surface and test whether
   key identity or timing can be recovered from the retained band.
4. **Footsteps and occupancy.** Test whether footstep timing or number of occupants can be inferred
   from the accumulators, and over which window lengths.
5. **Body motion.** With the phone on a bed or sofa, test whether breathing or movement is visible in
   the retained band. Sessions only start when the phone is flat and still, which should exclude this;
   the gate must be tested on this case.
6. **Accumulator inversion.** Test whether per-session accumulators allow any reconstruction of the
   time series. Averaged cross-spectral sums discard phase relationships between windows, which should
   prevent it; this is expected, not shown.
7. **Tier B sync frames.** These carry complex spectra below 5 Hz and so more information than the
   accumulators. Test them separately; they stay opt-in until this is done.

Until these tests pass, public statements say "by design" and not "proven".

## 3. Data inventory

Retention periods are PROPOSED and must be set by the controller with legal advice.

| Field | Purpose | Retention (PROPOSED) | Identifiability |
|---|---|---|---|
| Session id (random) | De-duplicate uploads | Same as the session record | Low alone; not linked to an account |
| Contributor pseudonym (salted per building) | Count distinct contributors for the K-threshold; support deletion | While contributions are held | Pseudonymous. Cannot be matched across buildings. Re-identifiable by whoever holds the device secret |
| Building id | Attribute the session | Life of the building record | Building-level; becomes personal data when tied to one household |
| Floor estimate and method | Mode shape, amplitude scaling | With the session | Weak. Narrows the location within a building |
| Start and end time (rounded to the minute) | Excitation context, change detection | With the session; published only as building-level aggregates | Reveals night-time presence of a contributor in a building if the building has few contributors |
| Sync quality | Server weighting | With the session | None alone |
| Device model and sensor name | Noise model, fleet artefact check | With the session | Low alone; a rare model plus building plus time can single out a phone |
| Measured rate, window counts | Quality control | With the session | None alone |
| Spectral accumulators | Identification | While needed for stacking and deletion (section 7) | Not intelligible as signals; see section 2 tests |
| Five-band noise summary | Per-model noise floor | With the session | None alone |
| Battery temperature, level at start and end | Battery cost, temperature regression | With the session | None alone |
| Tier B sync frames (opt-in) | Cross-phone coherence | PROPOSED shorter than other fields | Higher: complex spectra |
| Coarse location fix and footprint query | On-device building match | Never sent to the server beyond the point rounded to 0.01 degrees (about 1 km) used for the footprint request; not stored or logged by the application | The request reveals the neighbourhood. This is a residual risk (section 8) |

The rounded point in the footprint request is the one place where location-derived information reaches the
server. It is a request parameter; the server should not log it with any contributor identifier.

## 4. Pseudonymous contributor ids

A contributor pseudonym is derived on the device from a secret stored in the app and the building id
(PROPOSED: a keyed hash of the building id under the device secret). Properties:

- Different per building, so two buildings cannot be linked by pseudonym.
- Stable within a building, so the K-threshold can count distinct contributors.
- Not reversible without the device secret.
- Counts devices, not people: one household with three phones counts as three. See section 5.

## 5. The K-threshold

Building outputs are released only when at least 3 distinct contributors and 5 sessions are combined
(defaults, `DESIGN.md` section 8). Below that the building appears as "needs data" with no parameters.

**What it protects against.** A single household's routine or presence being inferred from a
published building result, and trivial attribution of a result to one phone.

**What it does not protect against.**

- A small building with one contributing household and two visitors. If a household's phones or a
  few guests supply the three pseudonyms, the output is still dominated by one household, and a
  neighbour who knows who lives there can attribute it.
- Several phones of one household counting as several contributors.
- Deliberate inflation of the contributor count by one person using several devices.
- Differencing attacks: if outputs are released after each new session, the change between releases
  reveals what the latest contributor's sessions added. Release cadence matters.
- Inference from the existence of a building in the coverage map. "Needs data" tells an observer that
  nobody has contributed enough, and the opposite at release time.
- Anything that comes from the building id itself being identifying (a detached house).

Mitigations to consider: raise `K_c` for buildings with few units; release on a fixed schedule, not on
arrival; suppress buildings whose footprint implies a single dwelling; require contributors to confirm
that they live or work in different units. None are decided.

## 6. Time rounding

Session start and end are rounded to the minute on the device. Published outputs carry only
building-level aggregates, no per-session times. Rounding to the minute removes sub-minute timing but
not the overnight pattern. It does not hide that a phone was in a building between roughly two clock
times. The pattern is visible to the server in the stored session records and is therefore personal
data in the controller's hands, even though it is never published.

## 7. GDPR mapping

This maps the design to the usual headings. It is not an opinion on compliance.

**Roles.** The operating company is the controller for contributor data. Hosting and any other
service provider that processes data on its instructions is a processor and needs a processing
agreement. Insurers who buy building-level outputs receive data that, once the K-threshold is met, is
intended to be non-personal at building level; whether that holds for small buildings is a legal
question (section 5). Joint-controller questions arise if a partner runs its own collector app.

**Lawful basis.** Consent, collected in the app on the opt-in screen, specific to this purpose,
withdrawable in the app at any time. Withdrawal must be as easy as giving consent.

**Special categories.** None are intended to be collected: no health, biometric, religious or similar
data. The residual possibility that body motion could appear in the retained band is tested in section
2 item 5. If it cannot be excluded, the analysis changes.

**Data-subject rights.**

| Right | How it is met | Limit |
|---|---|---|
| Information | Opt-in screen plus a full privacy notice | Per language and country |
| Access | The app shows the contributor's sessions it holds records of | The server cannot find a person without the app's secret |
| Erasure | See below | Aggregates already combined |
| Withdrawal of consent | In-app switch stops collection and triggers erasure | |
| Objection, restriction, portability | Handled through the app; the design needs a per-session export | Not built |

**Deletion with pseudonymous contributions.** The server holds no account and cannot look up a person.
The app keeps the secret from which the per-building pseudonyms are derived. To delete, the app
derives the pseudonym for each building it contributed to and sends a signed deletion request; the
server removes every session record carrying that pseudonym. A person who has lost the phone or
reinstalled the app without the secret cannot be found and cannot erase, which must be stated in the
privacy notice. Design questions that remain open:

- Per-session accumulators must be kept until they are folded into a building stack. Once folded,
  removing one session's contribution needs either retained per-session records or a re-stack from the
  remaining sessions. PROPOSED: keep per-session accumulators for as long as the building is active
  and rebuild the stack on deletion.
- Published scores built partly from the deleted sessions need a recompute and a re-release.
- Backups need a deletion cycle.

**DPIA.** Treat a data protection impact assessment as required before launch. Likely triggers:
systematic monitoring of a publicly accessible or residential area; large-scale processing; use of a
new technology; the combination of building-level risk scores with insurance use. A regulator's list
of triggers differs by country.

**International transfers.** Contributors in one country, servers or insurer customers in another.
Hosting region is a design choice (PROPOSED: host in the contributor's region). Transfers of
pseudonymous session data, and of outputs to insurers outside the region, need a transfer mechanism
chosen with legal advice.

**Records of processing.** Keep a record of processing for each processing purpose: contributor
sessions, building aggregates, scoring, delivery to insurers, support and deletion requests. Keep a
data-flow diagram and a processor list with each launch.

## 8. Residual risks and open questions

1. The 25 Hz guarantee is by design and not yet tested (section 2).
2. K-threshold weakness for small buildings and multi-device households (section 5).
3. The footprint request exposes a coarse location (about 1 km) to the server.
4. Device model plus building plus time can fingerprint a phone.
5. Deletion cannot reach contributors who lost the app secret; folded aggregates need a recompute.
6. Whether building-level outputs are non-personal data for small buildings.
7. Whether tier B sync frames can be offered under the same consent.
8. Retention periods are not set.
9. Insurer use of building scores raises fairness issues outside data protection; see
   `docs/responsible_use.md`.
10. Rules on consent age, consumer location data and use for insurance differ by country.

## 9. What a lawyer must review per launch country

- Consent wording and withdrawal mechanics in the local language
- Whether any rule treats the data as location data or as device data needing separate consent
- Controller and processor contracts and hosting location
- The DPIA, and whether the regulator must be consulted
- Rules on transfers to the insurer and to any non-local recipient
- Rules limiting the use of such data in insurance pricing
- Retention and deletion obligations
- The ODbL and other licence questions in `docs/licences.md`, which interact with what is delivered
