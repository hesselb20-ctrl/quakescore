# QuakeScore

QuakeScore estimates a building's natural frequencies and damping from the ambient vibration picked
up by phones lying still inside it, and maps those measurements to a seismic vulnerability score
with an uncertainty band. It is a statistical screening layer, not a structural engineering
assessment.

**Where the project stands.** Everything that can be built and measured on a computer is built and
measured in simulation. Nothing has been measured on a real building yet, because that needs phones
in buildings. Read `docs/REPORT.md` first: it separates what works on real buildings (nothing yet),
what works in simulation, what failed, and the next steps.

Every number in this repository carries one of four labels: `REAL` (measured on a real building),
`SIM` (simulator), `REF` (cited publication), `ASSUMED` (engineering assumption not yet measured).

## Layout

| Path | What it is |
|---|---|
| `DESIGN.md` | Signal chain, identification, vulnerability mapping, privacy, validation plan |
| `docs/REPORT.md` | Final report: results, failures, next steps |
| `docs/pitch/` | Technical note for reinsurers and catastrophe modellers |
| `docs/references.md` | Verified citations and published reference values |
| `docs/validation_protocol.md` | Field protocol for the collector test and real-building validation |
| `docs/privacy.md`, `docs/responsible_use.md`, `docs/licences.md` | Privacy design, use rules, licences |
| `docs/platforms.md`, `docs/api.md` | Android and iOS differences, upload schema, API |
| `quakescore/sim` | Building, excitation, phone and interference simulator (time-domain and fast spectral path) |
| `quakescore/device` | Reference on-device feature pipeline |
| `quakescore/ident` | Stacking, detection, curve fit, EFDD, SSI-COV, random decrement, FDD, bootstrap |
| `quakescore/artefacts` | Rejection of non-structural peaks |
| `quakescore/vuln` | Class model, capacity spectrum method, fragility, QuakeScore |
| `quakescore/change` | Frequency tracking and change detection |
| `quakescore/product.py` | Batch job from sessions to building records |
| `quakescore/service` | API, storage, portfolio matching, coverage |
| `dashboard` | Static demo dashboard (MapLibre GL, OpenStreetMap tiles) |
| `android`, `ios` | Collector app sources (written, not yet compiled or run) |
| `experiments` | One script per milestone; outputs in `results/` |
| `results/*_summary.md` | Measured tables per milestone |

## Run it

```bash
python -m venv .venv
```

```bash
.venv/Scripts/python -m pip install numpy scipy pytest fastapi uvicorn httpx python-multipart matplotlib markdown
```

```bash
.venv/Scripts/python -m pytest -q
```

Experiments (set `PYTHONPATH=.`; each writes JSON and a Markdown summary under `results/`):

| Command | Milestone | Rough time on 6 cores |
|---|---|---|
| `python experiments/m1_run.py` then `python experiments/m1_report.py` | 1: simulator and identification | 30 min |
| `python experiments/export_device_vectors.py` | 2: test vectors for the Kotlin DSP | 1 min |
| `python experiments/m3_validate_real.py <session folder>` | 3: real-building comparison | seconds |
| `python experiments/m4_artefacts.py` | 4: artefact rejection | 10 min |
| `python experiments/m5_vulnerability.py` | 5: vulnerability model | 4 min |
| `python experiments/m6_change.py` | 6: change detection | 15 min |
| `python experiments/demo_city.py` then `python experiments/summaries.py` | 7: demo city records | 10 min |
| `python experiments/make_figures.py` | 8: figures for the technical note | 1 min |

API and dashboard:

```bash
.venv/Scripts/python -m uvicorn quakescore.service.app:app
```

See `docs/api.md` for loading footprints and results, and for exporting the static dashboard data.

## What is needed to get the first real measurement

1. Build the Android app (`android/README.md`): it needs a JDK and the Android SDK, which were not
   available where this was written, so the Kotlin has never been compiled.
2. Run the field protocol in `docs/validation_protocol.md`.
3. Drop the uploaded session files into a folder and run `experiments/m3_validate_real.py`.

## Data and licences

Footprints in `data/demo_city` are from OpenStreetMap contributors (ODbL). Fragility parameters are
from the FEMA Hazus 6.1 technical manual. See `docs/licences.md` for what has to be settled before
any data is sold.
