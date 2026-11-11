# Licences

Two lists: software dependencies (must be MIT, BSD or Apache) and data sources. This is a tracking
document, not legal advice. Data licence facts come from `docs/research/codes_and_fragility.md`
sections 5 and 6. Software licence names are recorded from the project's intended stack and have not
been checked against the packages.

## 1. Software dependencies

Rule: every runtime, build and test dependency is MIT, BSD or Apache-2.0. No GPL, AGPL, LGPL or
non-commercial licence enters the repository or the shipped apps.

None of the licences below could be verified from the research files. Each row is
**to confirm at release against each package's LICENSE file**, including transitive dependencies.

| Dependency | Use | Expected licence | Status |
|---|---|---|---|
| NumPy | simulator, identification | BSD-3 | To confirm at release against the package's LICENSE file |
| SciPy | filters, spectra, optimisation | BSD-3 | To confirm at release against the package's LICENSE file |
| FastAPI | service | MIT | To confirm at release against the package's LICENSE file |
| Uvicorn | ASGI server | BSD-3 | To confirm at release against the package's LICENSE file |
| Pydantic | schemas | MIT | To confirm at release against the package's LICENSE file |
| httpx | client and tests | BSD-3 | To confirm at release against the package's LICENSE file |
| pytest | tests | MIT | To confirm at release against the package's LICENSE file |
| MapLibre GL JS | dashboard map | BSD-3 | To confirm at release against the package's LICENSE file |
| OkHttp | Android networking | Apache-2.0 | To confirm at release against the package's LICENSE file |
| AndroidX libraries | Android app | Apache-2.0 | To confirm at release against the package's LICENSE file |
| Kotlin | Android language and stdlib | Apache-2.0 | To confirm at release against the package's LICENSE file |
| H3 | spatial index | Apache-2.0 | To confirm at release against the package's LICENSE file |

Release check: generate a full dependency list including transitive packages for Python and Gradle,
record each licence from the package's own LICENSE file, and fail the release on any licence outside
the allowed set. Postgres/PostGIS and SQLite are infrastructure, not linked dependencies; their terms
are not assessed here.

Code that must not be used even though it is public: the GEM taxonomy repository's code is AGPL v3
(section 2.5). Do not copy or import it.

## 2. Data licences

### 2.1 Summary

| Source | Licence (as recorded) | Commercial use in a paid product | Action |
|---|---|---|---|
| OpenStreetMap data | ODbL; credit OpenStreetMap and state the data is under ODbL | Not stated in the research files | Legal question, section 2.2, before selling data keyed to OSM ids |
| OSM tiles (tile.openstreetmap.org) | Tile usage policy, not a data licence | Heavy use may be blocked without notice, no SLA | Do not depend on it for production, section 2.3 |
| Overture buildings | ODbL for the theme; mixed source licences | Same question as OSM | Section 2.4 |
| Hazus 6.1 | FEMA technical manual; no licence terms recorded in the research files | Not stated | Confirm terms of use, section 2.5 |
| GEM Building Taxonomy | Data CC BY-SA 4.0; code AGPL v3 | CC BY-SA permits commercial use with attribution and share-alike | Labels only, section 2.6 |
| GEM global vulnerability model | CC BY-NC-SA 4.0 | **Not allowed** under the public licence | Do not use, section 2.6 |
| Damage datasets | Varies | Varies | Section 2.7 |

### 2.2 OpenStreetMap: the share-alike question

What the research file confirms: OSM data is under the Open Data Commons Open Database License
(ODbL). Users must credit OpenStreetMap (display the attribution notice) and make clear the data is
available under the ODbL; a link to https://www.openstreetmap.org/copyright suffices.

What it does not contain: the ODbL text. The share-alike terms were not read here, so this file does
not state what they require.

The question to settle, in the terms the product raises it:

- QuakeScore stores one row per building, keyed to an OSM id, with modal frequency, damping, class
  probabilities and a score. That is data derived from, and joined to, an OSM-identified object.
- The ODbL distinguishes between a "produced work" (for example a map or an image made from the data)
  and a "derived database" (a database built from the data). Which of these a per-building score table
  keyed to OSM ids is, and what share-alike then requires of it, is a legal question.
- The commercial consequence is large. If a share-alike obligation attached to the whole table, the
  product would have to be offered under ODbL, which is incompatible with selling it as proprietary
  data. If only the OSM-derived part (ids, footprints) is affected, the measured parameters could be
  kept separate and joined by id on the customer side.

**Decision needed before any data keyed to OSM ids is sold.** Options to put to a lawyer:

1. Key the product to our own building id and ship the OSM id mapping separately.
2. Ship only the measured fields and a join key, with no OSM attributes in the delivered table.
3. Build the product on a footprint source with a permissive licence (see Overture sources below).
4. Accept ODbL for the delivered table.

Attribution is required in every case: a visible "(c) OpenStreetMap contributors" on the dashboard and
a licence statement in the API documentation and data exports.

### 2.3 OSM tile usage policy

Source: https://operations.osmfoundation.org/policies/tiles/ (page undated). Recorded rules: heavy
use may be blocked without notice; no SLA; show "(c) OpenStreetMap contributors"; send a distinct,
stable User-Agent and a valid Referer; honour cache headers (at least 7 days if they cannot be read);
use HTTPS. Prohibited: bulk downloading or pre-seeding areas, building tile archives, wide-area
automated scans (especially at z >= 14), headless panning bots, offline-download features.

Consequence: the demo dashboard may use OSM tiles within these rules. A commercial dashboard should
not depend on tile.openstreetmap.org; use a tile provider with a service agreement or self-hosted
tiles. Choice of provider is open.

### 2.4 Overture Maps buildings

Source: https://docs.overturemaps.org/attribution/. Licence for the buildings theme: ODbL. Listed
sources and licences: OpenStreetMap contributors (ODbL), Esri Community Maps contributors (CC BY 4.0),
Microsoft Global ML Building Footprints (ODbL), Google Open Buildings (CC BY 4.0), USGS 3D Elevation
Program (no licence stated), Qian Shi et al. (Zenodo 10.5281/zenodo.8174931, CC BY 4.0), derived from
BTN 2024 from ign.es (CC BY 4.0). Attribution in Overture's tool: "(c) OpenStreetMap contributors,
Overture Maps Foundation".

- The theme is ODbL as a whole, so the question in 2.2 applies to Overture ids as well.
- Which sources feed a given building is per-record, so a permissive-only subset would need filtering
  by source. Not investigated.
- The release version of the buildings data was not checked and the page is undated.

### 2.5 Hazus

Source: FEMA Hazus Earthquake Model Technical Manual, Hazus 6.1, July 2024. The product brief
describes Hazus as a US federal publication. The research files record no licence or terms-of-use text
for it. **To confirm:** the terms of use of the manual and software, and whether reuse of its published
parameter values in a commercial product needs any notice or permission. Cite the manual wherever the
parameters are used. Only the 6.1 edition has been read.

### 2.6 GEM taxonomy and GEM global vulnerability model

| Item | Licence | Consequence |
|---|---|---|
| GEM Building Taxonomy, data (spreadsheets, definitions) | CC BY-SA 4.0 (DATA_LICENSE) | Commercial use allowed with attribution and share-alike |
| GEM Building Taxonomy, code (oq-gem-taxonomy, repository code) | GNU AGPL v3 | Do not link, copy or import |
| GEM global vulnerability model (v2026.0.0) | CC BY-NC-SA 4.0 | Commercial use not allowed. The README says commercial use needs a specific licence agreement (product@globalquakemodel.org; other use cases license@globalquakemodel.org) |
| GEM global exposure model | Licence file not read | NOT VERIFIED |

Product decision: **the paid product uses Hazus parameters (section 2.5) for fragility and capacity.
It does not use the GEM global vulnerability model in any form, and does not train, calibrate or tune
against it.** GEM taxonomy strings are used only as labels on classes.

Open points for a lawyer:

- **Share-alike on the taxonomy data.** CC BY-SA 4.0 applies share-alike to adapted material. Whether
  attaching taxonomy strings to rows in a proprietary table, or reproducing taxonomy attribute names
  and codes in outputs, counts as an adaptation that triggers share-alike is not settled here. The
  safest course is to use a minimal set of string codes as identifiers, give attribution, and keep
  nothing else from the taxonomy tables in the product.
- Fragility functions are not in the GEM repository (the README sends users to GEM for them), so there
  is nothing to take from there in any case.
- If a future version wants GEM vulnerability curves, it needs a commercial agreement first.

### 2.7 Damage datasets

Used only for class-level comparison against the score (`DESIGN.md` section 9), not as a product input.
Licences as recorded; check each before any use beyond internal validation.

| Dataset | Licence recorded | Note |
|---|---|---|
| ACI 133 Turkey RC database, Zenodo 10.5281/zenodo.13386343 | CC BY 4.0 (Zenodo metadata) | About 240 RC buildings; storeys, height and damage class per building |
| Building damage datasets for the 2023 Turkiye earthquake (Liu), Zenodo 10.5281/zenodo.18437501 | CC BY 4.0 (Zenodo metadata) | Remote-sensing damage, not field-surveyed; zip contents not opened |
| Copernicus EMS EMSR648 | No licence stated on the activation page | NOT VERIFIED; terms page not read |
| StEER 2023 Kahramanmaras, DesignSafe PRJ-3824, EERI/SSEER PRJ-5797 | NOT VERIFIED | Pages returned HTTP 403 |
| Da.D.O. (EUCENTRE) | No licence or terms on the page read | Access-controlled; per-building download rights NOT VERIFIED |
| Mendeley Data cfp65g3v3c (Bernardini et al. 2019), 2016 Central Italy | CC BY NC 3.0 | **Non-commercial.** 50 structural units; do not use in a commercial product or in material sold with it |

CC BY 4.0 datasets need attribution in any document that uses them. Any dataset with a non-commercial
or unstated licence stays out of the shipped product and out of the sold data.

## 3. Attribution checklist for release

- [ ] "(c) OpenStreetMap contributors" visible on the dashboard map and in the API documentation
- [ ] Overture attribution line if Overture footprints are used
- [ ] GEM taxonomy attribution (CC BY-SA 4.0) where strings appear
- [ ] Hazus 6.1 cited where parameters are used
- [ ] CC BY 4.0 dataset citations in validation documents
- [ ] Dependency licence report generated and reviewed (section 1)
- [ ] Written legal opinion on section 2.2 filed before the first data sale
