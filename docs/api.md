# QuakeScore API and data product

The data-product layer: upload codec, storage, coverage engine and K-threshold gate, portfolio
matching, exports, and the static demo dashboard. Code: `quakescore/service/`, `dashboard/`.

QuakeScore is a statistical screening layer. It is not a structural engineering assessment, and every
public surface says so.

## 1. Run locally

```sh
# from the repository root, with PYTHONPATH set to it
python -m quakescore.service.build_demo          # footprints + results + static export, one command
uvicorn quakescore.service.app:app --no-access-log --port 8000
python -m http.server 8080 --directory dashboard # static dashboard: http://127.0.0.1:8080/
# live mode: http://127.0.0.1:8080/?api=http://127.0.0.1:8000  (add the API key under About)
```

Run uvicorn with `--no-access-log`. The application never logs requests itself, and a middleware
(`PrivacyScrubMiddleware`) blanks the query string and client address in the ASGI scope before the
response starts, so a server access log that was left on records neither coordinates nor IP
addresses (verified with uvicorn's default access log during development: lines read
`INFO:      - "GET /v1/footprints HTTP/1.1" 200 OK`). Reverse proxies and hosting platforms keep their
own logs; configure those separately (section 9).

Configuration (environment variables, read in `quakescore/service/config.py`):

| Variable | Default | Meaning |
|---|---|---|
| `QS_DB` | `data/quakescore.sqlite` | SQLite database path |
| `QS_BLOB_DIR` | unset | store session feature blobs as files here instead of in SQLite |
| `QS_K_CONTRIBUTORS` | 3 | release threshold: distinct contributors |
| `QS_K_SESSIONS` | 5 | release threshold: sessions |
| `QS_API_KEYS` | `demo-key` | comma-separated buyer keys. **Placeholder authentication**: a static key list is not production auth (no rotation, scoping, rate limits or audit). The default key exists for local development only. |
| `QS_CORS_ORIGINS` | `*` | origins allowed to call the API from a browser |
| `QS_INSPECTION_URL` | `docs/responsible_use.md` | inspection route shown on the resident card |
| `QS_MAX_UPLOAD_MB` | 2 | maximum compressed upload size |

## 2. Loading data

```sh
python -m quakescore.service.load_footprints data/demo_city/footprints.geojson
python -m quakescore.service.load_results results/demo_city/buildings.json --replace
python -m quakescore.service.export_static dashboard/data
```

**Swapping FIXTURE records for the real batch output is one command:**
`python -m quakescore.service.build_demo`. It loads `results/demo_city/buildings.json` when that file
exists (replacing every stored record) and otherwise generates FIXTURE records
(`quakescore/service/fixtures.py`, fabricated placeholders labelled `FIXTURE`), then re-exports
`dashboard/data`. `--fixture` forces the placeholders. At the time of writing the batch file exists
and holds 24 `SIM` records, so the exported dashboard shows those (18 released, 3 needs data, the
other footprints have no record and show as "no data").

`load_results` validates every record (provenance label, coverage fields, `lo <= value <= hi` for the
score, f1 and every mode) and rejects invalid ones; they are never served. A record whose building has
no stored footprint is added as a point at `attrs.lat/lon`.

Demo footprints come from `experiments/fetch_footprints.py` (one Overpass request, downtown San
Francisco, bbox S 37.7860 W -122.4050 N 37.7960 E -122.3920). Attribution and licence (ODbL) are in
`data/demo_city/ATTRIBUTION.md`. If Overpass is unreachable the script writes a grid in which every
feature has `properties.synthetic = true`; the dashboard banner then says "synthetic footprints".

## 3. K-threshold and release rules

A building's parameters and score are released only when its result record satisfies all of:

- `coverage.contributors >= K_c` (default 3) and `coverage.sessions >= K_s` (default 5),
- `coverage.status == "scored"`,
- a score with a complete band (`value`, `lo`, `hi`, `lo <= value <= hi`).

Otherwise every endpoint returns coverage only (`sessions`, `contributors`, `floors`, `status`,
`sessions_needed`, `contributors_needed`): no modes, f1, damping, class, stiffness, score, damage,
drift or spectrum. There is one gate (`coverage.building_view`) used by the API, the portfolio matcher
and the static export. Every released object carries `provenance` and the uncertainty band. No
endpoint returns a score without its band.

Coverage counts shown are the larger of the record's counts and the live `sessions` table, since
uploads arrive between batch runs. `sessions_needed = max(K_s - sessions, K_c - contributors)`
(every new contributor brings at least one session).

When a contributor deletes a session (section 5.2) the building is marked for recomputation. Until the
batch writes a new record, the record's own counts are no longer trusted: coverage and the threshold
use the live sessions table only, the view carries `"recompute_pending": true`, and the result is
withheld if the remaining live sessions fall below K.

## 4. Upload schema (schema 1)

`POST /v1/sessions`, body JSON, optionally gzip (`Content-Encoding: gzip`, or detected from the gzip
magic bytes). Codec: `quakescore/service/codec.py` (`encode`, `decode`, `validate`).

```json
{
  "schema": 1,
  "session_id": "6f1c2a0e-8a63-4c8e-9a51-2b0c4b7f1d22",
  "building_id": "osm:way/123",
  "contributor": "3fa94c0e1b2d7a65",
  "phone_model": "Pixel 8", "sensor_name": "LSM6DSO",
  "floor": 4, "floor_method": "baro_entry",
  "t_start": 1790000040, "duration": 3600, "fs_raw": 203.7, "lsb": 0.0012,
  "sync_source": "ntp", "sync_sigma_ms": 12.0, "accept_fraction": 0.81, "temp_c": 27.5,
  "battery_start": 80, "battery_end": 100, "charging": true,
  "platform": "android", "app_version": "0.3.1",
  "bands": {
    "L": {"k": 8, "csd": "<base64 float32 LE, 1025*9>", "p4": "<base64 float32 LE, 1025*3>"},
    "M": {"k": 30, "csd": "...", "p4": "..."},
    "H": {"k": 120, "csd": "...", "p4": "..."}
  }
}
```

- `csd` per bin: `Gxx, Gyy, Gzz, Re Gxy, Im Gxy, Re Gxz, Im Gxz, Re Gyz, Im Gyz`, with
  `G_ij = mean over windows of X_i conj(X_j)`, one-sided, (m/s^2)^2/Hz. The server rebuilds the
  Hermitian 3x3 matrix. `p4` per bin: mean `|X_i|^4` for x, y, z.
- Validation is strict: canonical uuid4 `session_id`; `contributor` 16 lowercase hex; `t_start` UTC
  seconds, a multiple of 60, between 2020-01-01 and now + 2 days; finite numbers within plausible
  ranges; exact byte sizes; non-negative auto-spectra and `p4`; `k >= 0`; at least one band.
- **Any field not in schema 1 is refused (422). A field whose name looks like location** (`lat`,
  `lon`, `lng`, `gps`, `location`, `geo`, `coords`, `altitude`, `address`, `wifi`, `bssid`, `ip`,
  `cell_id`, `h3`, ...) **is refused with an explicit "location fields are never accepted" message**,
  at the top level and inside band objects, so location cannot be stored by accident.
- `provenance` is optional and only the simulator sets it (`"SIM"`); uploads without it are `REAL`.
  `floor_method: "sim"` is accepted only on `SIM` payloads.
- Tier-B sync frames are not part of schema 1.

Responses: `201 {"status": "stored", "session_id": ...}`; repeat of a stored `session_id`:
`200 {"status": "duplicate"}` (idempotent; the first upload wins); `422 {"detail": {"field", "error"}}`
for validation failures or an unknown `building_id`; `400` for bad gzip/JSON (NaN and Infinity
literals are refused); `413` for oversize bodies (2 MB compressed, 8 MB decompressed).

Stored per session: session id, building id, contributor pseudonym, the date received (no time), the
validated metadata, and the features as a gzip blob. No IP address, no location, no account.

## 5. Endpoints

Public endpoints need no key. Buyer endpoints need `X-API-Key: <key>` and return 401 otherwise.
Building ids contain a slash (`osm:way/123`); use them as-is in paths (`/v1/buildings/osm:way/123`) or
percent-encode the slash.

### 5.1 `POST /v1/sessions` (public, phone app)
See section 4.

### 5.2 `DELETE /v1/sessions/{session_id}` (public, "delete my contributions")
The random session id is the capability: the app keeps the ids of its own sessions and sends one
DELETE per session when the user chooses "delete my contributions". The server removes the session
row and its features (blob or file) and marks the building's result for recomputation (section 3).

```
DELETE /v1/sessions/6f1c2a0e-8a63-4c8e-9a51-2b0c4b7f1d22   ->  204 No Content
```
Always 204 whether or not the id existed, so ids cannot be probed; 422 only if the path is not a
uuid. The session id is also scrubbed from the path in any access log. Contributor pseudonyms are not
an authentication factor and cannot be used to delete.

### 5.3 `GET /v1/footprints` (public, phone app)
Two forms; both return GeoJSON with properties `id`, `name`, `address`, `storeys` only.

- `?lat=37.79&lon=-122.40` (what the Android app sends, coordinates rounded on the device to
  0.01 degrees): **every footprint whose outline intersects the box lat +-0.01, lon +-0.01 degrees**
  (`box_deg: 0.01` in the response). The coordinates are used for this one query and are neither
  stored nor logged by the application, and the client address is never read; see section 1 for how
  server access logs are scrubbed.
- `?cell=<id>[&ring=1]`: footprints whose centroid lies in that cell (plus its neighbours with
  `ring=1`). Cells: H3 resolution 8 when the `h3` package is importable; otherwise the documented
  fallback square grid of about 0.73 km^2 with ids `g8:<ix>:<iy>` (`quakescore/service/cells.py`). The
  `h3` package has no wheel for the Python used here, so the fallback is what was tested.

```json
{"type": "FeatureCollection", "box_deg": 0.01,
 "features": [{"type": "Feature", "id": "osm:way/123",
   "geometry": {"type": "Polygon", "coordinates": [[[-122.4, 37.79], ...]]},
   "properties": {"id": "osm:way/123", "name": null, "address": "100 Market Street", "storeys": 8}}]}
```

### 5.4 `GET /v1/buildings/{id}` (buyer)
The full record when released; otherwise the coverage-only view. Shape of a released view:

```json
{"building_id": "osm:way/123", "provenance": "SIM", "updated": "2026-11-11", "released": true,
 "recompute_pending": false,
 "attrs": {"storeys": 8, "height_m": 30.0, "year": 1965, "material": null, "use": null,
           "name": null, "address": "100 Market Street", "lat": 37.7901, "lon": -122.3998},
 "coverage": {"sessions": 12, "contributors": 4, "floors": 3, "status": "scored",
              "sessions_needed": null, "contributors_needed": null,
              "k_threshold": {"contributors": 3, "sessions": 5}},
 "modes": [{"f": 1.14, "f_lo": 1.13, "f_hi": 1.14, "zeta": 0.021, "zeta_lo": 0.017, "zeta_hi": 0.032,
            "z": 16.2, "label": "structural"}],
 "f1": 1.14, "f1_lo": 1.13, "f1_hi": 1.14, "zeta1": 0.021, "zeta1_lo": 0.017, "zeta1_hi": 0.032,
 "class_probs": {"S1H": 0.55, "S2H": 0.27}, "class_map": "S1H", "gem_taxonomy": "S/LFM/HEX:8",
 "stiffness": {"k_ratio": 1.08, "z": -0.15, "flag": false},
 "score": {"value": 69.1, "lo": 47.5, "hi": 84.8, "prior_value": 72.4, "prior_lo": 47.0, "prior_hi": 92.4},
 "damage": {"pga_0.15": {"slight": 0.32, "moderate": 0.30, "extensive": 0.08, "complete": 0.02}, "...": {}},
 "drift": {"pct_per_year": -0.72, "step_pct": null, "alert": false, "series": [["2026-01-15", 1.1457, 0.0037]]},
 "spectrum": {"band": "M", "f": [0.40, 0.42], "excess": [1.02, 0.98]}}
```
A view that is not released has the same `building_id`, `provenance`, `updated`, `released: false`,
`attrs` and `coverage`, and nothing else.

### 5.5 `GET /v1/buildings` (buyer)
`?bbox=west,south,east,north&min_score=&max_score=&status=scored|needs_data|no_data&provenance=&limit=`
(default 1000, max 20000). GeoJSON FeatureCollection; flat summary properties per feature: `id`,
`prov`, `status`, `released`, `sessions`, `contributors`, `sessions_needed`, `name`, `address`,
`storeys`, and for released buildings only `score`, `score_lo`, `score_hi`, `f1`, `f1_lo`, `f1_hi`,
`k_ratio`, `k_flag`, `drift_pct`, `drift_alert`, `class_map`. Score filters return released buildings
only.

### 5.6 `GET /v1/buildings/{id}/public` (public, resident card)
```json
{"building_id": "osm:way/400", "provenance": null, "name": null, "address": null,
 "status": "no_data", "sessions": 0, "contributors": 0, "sessions_needed": 5, "contributors_needed": 3,
 "score_band": null,
 "message": "No measurements yet. 3 different people and 5 sessions are needed before a result is published.",
 "caveat": "This is a statistical screening result ... It is not a structural engineering assessment ...",
 "inspection_route": {"text": "If you are concerned about this building, ask the owner ...", "url": "docs/responsible_use.md"}}
```
When released, `score_band` is `{"value", "lo", "hi", "interval": "5-95%", "scale": "0-100, 100 = least vulnerable", "provenance"}`.

### 5.7 `GET /v1/coverage?bbox=` (public)
Every building in the box with `status`, `sessions`, `contributors`, `floors`, `sessions_needed`,
`contributors_needed`, `provenance`; `meta.counts` per status. Never modal parameters or scores.

### 5.8 `POST /v1/portfolio` (buyer)
Multipart (`file` field) or a raw `text/csv` body, at most 5 MB / 10,000 rows. Columns
(case-insensitive, any subset): `building_id`; `lat`, `lon` (aliases `latitude`, `longitude`, `lng`);
`address`; optional `ref` (aliases `asset_id`, `id`, `name`) echoed back.

Matching order: (1) `building_id` exact; (2) lat/lon point-in-polygon, else the nearest footprint whose
edge is within 30 m; (3) address by normalised string match (lower case, punctuation removed,
`St`/`Ave`/`Blvd`/... expanded, text after the first comma ignored) against footprint address tags;
several footprints with one address give `ambiguous` with `candidates`. **No external geocoder in v1.**
Plug-in point: set `quakescore.service.portfolio.GEOCODER` to a callable `address -> (lat, lon) | None`;
unmatched addresses are then geocoded and matched as in (2), with method `geocoded+...`.

```json
{"job_id": "…",
 "summary": {"rows": 8, "matched": 5, "unmatched": 1, "ambiguous": 1, "invalid": 1, "scored": 3,
             "coverage_pct": 60.0, "coverage_pct_of_rows": 37.5,
             "match_methods": {"building_id": 1, "point_in_polygon": 2, "nearest_footprint": 1, "address": 1},
             "provenance": {"SIM": 5},
             "score_distribution": {"bins": [{"lo": 0, "hi": 20, "count": 0}, …], "median": 61.5,
                                    "p10": 52.0, "p90": 70.1, "n": 3}},
 "rows": [{"row": 1, "ref": "a", "building_id": "osm:way/100", "match_status": "matched",
           "match_method": "building_id", "distance_m": null, "note": null,
           "coverage_status": "scored", "sessions_needed": null, "provenance": "SIM",
           "score": {"value": 61.5, "lo": 51.5, "hi": 69.4}, "f1": {"value": 3.57, "lo": 3.48, "hi": 3.66}}]}
```
`GET /v1/portfolio/{job_id}` (buyer) returns a stored job.

### 5.9 `GET /v1/export.csv`, `GET /v1/export.geojson` (buyer)
Released buildings only. Columns: `building_id, provenance, updated, lat, lon, name, address, storeys,
score, score_lo, score_hi, prior_score, prior_lo, prior_hi, f1_hz, f1_lo_hz, f1_hi_hz, zeta1,
zeta1_lo, zeta1_hi, class_map, gem_taxonomy, k_ratio, stiffness_z, stiffness_flag, drift_pct_per_year,
drift_alert, sessions, contributors, floors`. Footprint data is ODbL; a public derived database must
carry the same licence.

### 5.10 `GET /v1/contributors/{pseudonym}/badges?building_id=` (public)
Referral loop, a pure function of the building's stored sessions ordered by `t_start`. Each own
session earns 1 point, or 2 if the building was still below the K-threshold when it was recorded.
Tiers by points: `first_reading` 1, `regular` 5, `anchor` 15, `cornerstone` 40.
```json
{"pseudonym": "aaaaaaaaaaaaaaaa", "sessions": 4, "under_covered_sessions": 3, "points": 7,
 "tier": "regular", "next_tier": {"name": "anchor", "points_needed": 8}, "pioneer": true,
 "building": {"sessions": 8, "contributors": 5, "sessions_needed": null, "contributors_needed": null},
 "invite_hint": null}
```
The pseudonym is salted per building on the phone, so it only reveals counts to whoever holds it.

### 5.11 `GET /v1/meta` (public)
Counts, result provenance counts, cell system, K-threshold, auth note.

## 6. Result record schema (batch job output)

One JSON object per building in a JSON list (`results/demo_city/buildings.json`):

```
{ "building_id": str, "provenance": "SIM"|"REAL"|"FIXTURE", "updated": ISO date,
  "attrs": {"storeys": int, "height_m": float, "year": int|null, "material": str|null, "use": str|null,
            "lat": float, "lon": float, "name": str|null, "address": str|null},
  "coverage": {"sessions": int, "contributors": int, "floors": int,
               "status": "scored"|"needs_data"|"no_data", "sessions_needed": int|null},
  "modes": [{"f", "f_lo", "f_hi", "zeta", "zeta_lo", "zeta_hi", "z", "label": "structural"|"rejected:<reason>"}],
  "f1", "f1_lo", "f1_hi", "zeta1", "zeta1_lo", "zeta1_hi": number|null,
  "class_probs": {"C1M": 0.4, ...}, "class_map": str, "gem_taxonomy": str,
  "stiffness": {"k_ratio", "z", "flag"} | null,
  "score": {"value", "lo", "hi", "prior_value", "prior_lo", "prior_hi"} | null,
  "damage": {"pga_0.15": {"slight", "moderate", "extensive", "complete"}, "pga_0.30": {...}, "pga_0.60": {...}} | null,
  "drift": {"pct_per_year", "step_pct", "alert", "series": [[ISO date, f_Hz, sigma_Hz], ...]} | null,
  "spectrum": {"band": "L"|"M"|"H", "f": [...], "excess": [...]} | null }
```
Frequencies in Hz, damping as a ratio (0.02 = 2%), intervals 90% for modal parameters and 5-95% for
the score. The dashboard reads `damage` as probabilities of being in each state (the remainder is
"none"); if the values are non-increasing and sum to more than 1 it treats them as exceedance
probabilities and converts.

## 7. Storage

- Development and tests: SQLite (`quakescore/service/store.py`) with tables `buildings`, `sessions`,
  `results`, `portfolio_jobs`, `recompute`, `meta`. Spatial queries use a bounding-box index plus exact
  point-in-polygon and edge-distance tests in Python (`geo.py`).
- Production: `quakescore/service/schema_postgis.sql` (Postgres + PostGIS + h3-pg, H3 res-8 cell
  column filled by trigger, GiST indexes on footprints and centroids, a check that a stored score has
  its band). **This SQL has not been executed in this environment** (no Postgres here); review and test
  it before use. The Python service has no Postgres driver yet.

## 8. Static dashboard

`dashboard/index.html` + `css/app.css` + `js/{app,charts,portfolio}.js`, no build step. MapLibre GL JS
4.7.1 from unpkg (pinned). It reads `dashboard/data/buildings.geojson`, `meta.json` and
`b/<id>.json` written by `export_static`, so it can be hosted on any static host. `?api=<url>` switches
it to the live API (with an API key entered under About and kept in session storage: full data;
without one: coverage map and resident cards only). `?debug=1` prints script errors and render counts
on the page.

Layers: QuakeScore (ColorBrewer PuOr, 0 orange = most vulnerable to 100 purple = least), stiffness
anomaly `k_ratio` (diverging around 1.0), frequency drift in %/year (diverging around 0), coverage
status (Okabe-Ito blue / orange). Buildings without a released value are hatched; buildings with no
measurements have a flat light fill. REAL buildings have a solid outline, SIM and FIXTURE a dashed one,
and a provenance filter can hide either. The header says "Simulated data" whenever SIM or FIXTURE data
is loaded, and every detail panel repeats it.

**OSM tiles.** The basemap uses `tile.openstreetmap.org` raster tiles with the required
"© OpenStreetMap contributors" attribution. The OSM Foundation tile usage policy allows light use
only, with no heavy or bulk traffic and no guarantee of service. This is acceptable for a demo; a
production deployment needs its own tile source (a commercial provider or self-hosted vector tiles).

## 9. Deployment notes (free tiers)

**Nothing has been deployed.** A plausible free-tier layout:

- Static dashboard: any static host (GitHub Pages, Cloudflare Pages, Netlify). Upload `dashboard/`.
- API: a small container or Python host (for example Fly.io, Render or Google Cloud Run free tiers)
  running `uvicorn quakescore.service.app:app --no-access-log`, with `QS_API_KEYS` set to real secrets
  and `QS_CORS_ORIGINS` set to the dashboard origin. SQLite on a persistent volume is enough for a
  pilot; move to Postgres + PostGIS (for example a Supabase or Neon free tier, both offer PostGIS) using
  `schema_postgis.sql` once the service has a Postgres store. Session blobs belong in object storage.
- Platform request logs (load balancer, CDN, PaaS router) record IP addresses and full URLs outside the
  application; disable or minimise them, or keep retention short, and cover them in `docs/privacy.md`.
- Replace the static key list with real buyer authentication before any paying customer.

## 10. What was and was not tested here

Tested (pytest, `tests/test_service_codec.py`, `tests/test_service_api.py`; 39 tests pass):
codec round trip (bit-exact float32, Hermitian rebuild, packing order), strict validation, refusal of
location fields at the top level and inside bands, SIM provenance handling, cells and geometry helpers,
upload storage and idempotency (gzip and plain), K-threshold gating on every read path (building
detail, listing and its filters, coverage, resident card, CSV and GeoJSON export, portfolio, static
export), configurable K, that a score without a band is never released, buyer key enforcement,
footprints by box and by cell, portfolio matching by every method (id, point-in-polygon, nearest within
30 m, address, ambiguous address, fallback after an unknown id, invalid rows), badges, session
deletion (204 for known, repeated and unknown ids, recompute mark, withholding of a stale record),
and the access-log scrubbing middleware.

Also checked by hand: the dashboard in headless Chrome at 1280x820 (light and dark) and 390x844
(map layers, detail panel, charts, portfolio sample in static and live mode, live mode with and
without an API key) with no console errors; uvicorn's access log with the scrubber (no IP, no query
string).

Not tested: the PostGIS schema (not executed), the `h3` code path (package not installable here), any
deployment, real phone uploads (the Android app was written in parallel and was not run against this
API), load or concurrency beyond SQLite's single-writer lock, screen readers, and the dashboard in
Safari or Firefox.
