# Attribution

`footprints.geojson` contains building footprints and tags from OpenStreetMap.

Data (c) OpenStreetMap contributors. Available under the Open Database Licence (ODbL 1.0):
https://opendatacommons.org/licenses/odbl/1-0/ . See https://www.openstreetmap.org/copyright .

Any derived database that is publicly used must be offered under the ODbL as well.

Fetched 2026-11-11T17:14Z from the Overpass API (https://overpass-api.de) for bbox
south 37.7860, west -122.4050, north 37.7960, east -122.3920 (downtown San Francisco),
by `experiments/fetch_footprints.py`. Storeys come from `building:levels`, else `height / 3.3`,
else they are left empty.
