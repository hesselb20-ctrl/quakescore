"""Fetch demo building footprints from OpenStreetMap (Overpass API) for a small area of downtown
San Francisco and write them as GeoJSON to data/demo_city/footprints.geojson.

    python experiments/fetch_footprints.py            # one request to Overpass
    python experiments/fetch_footprints.py --synthetic  # skip the network, write a labelled grid

One polite request, no retry loop. If Overpass cannot be reached the script writes a clearly
labelled synthetic grid instead (every feature has properties.synthetic = true and the collection
has "synthetic": true), so synthetic footprints can never be mistaken for real ones.

Data: (c) OpenStreetMap contributors, available under the Open Database Licence (ODbL 1.0).
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "demo_city"
OUT = OUT_DIR / "footprints.geojson"
ATTRIB = OUT_DIR / "ATTRIBUTION.md"

BBOX = {"south": 37.7860, "west": -122.4050, "north": 37.7960, "east": -122.3920}
ENDPOINT = "https://overpass-api.de/api/interpreter"
USER_AGENT = "QuakeScoreDemo/0.1 (footprint fetch for a research demo)"
STOREY_HEIGHT_M = 3.3

TAGS_KEPT = ["building", "building:levels", "height", "start_date", "building:material", "name",
             "addr:housenumber", "addr:street", "addr:city", "addr:postcode", "roof:levels",
             "building:use", "amenity"]


def overpass_query(b: dict) -> str:
    bb = f'{b["south"]},{b["west"]},{b["north"]},{b["east"]}'
    return (f"[out:json][timeout:90];("
            f'way["building"]({bb});'
            f'relation["building"]["type"="multipolygon"]({bb});'
            f");out body;>;out skel qt;")


def fetch(b: dict) -> dict:
    data = urllib.parse.urlencode({"data": overpass_query(b)}).encode()
    req = urllib.request.Request(ENDPOINT, data=data, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


def _num(s) -> float | None:
    if s is None:
        return None
    m = re.match(r"\s*([0-9]+(?:\.[0-9]+)?)", str(s))
    return float(m.group(1)) if m else None


def _year(s) -> int | None:
    if not s:
        return None
    m = re.search(r"(1[6-9][0-9]{2}|20[0-9]{2})", str(s))
    return int(m.group(1)) if m else None


def _ring_closed(r: list) -> list:
    if r and r[0] != r[-1]:
        r = r + [r[0]]
    return r


def _assemble_rings(ways: list[list[int]]) -> list[list[int]]:
    """Join outer way segments end to end into closed rings (simple cases only)."""
    segs = [list(w) for w in ways if len(w) >= 2]
    rings = []
    while segs:
        cur = segs.pop(0)
        changed = True
        while cur[0] != cur[-1] and changed:
            changed = False
            for i, s in enumerate(segs):
                if s[0] == cur[-1]:
                    cur += s[1:]
                elif s[-1] == cur[-1]:
                    cur += s[::-1][1:]
                elif s[-1] == cur[0]:
                    cur = s[:-1] + cur
                elif s[0] == cur[0]:
                    cur = s[::-1][:-1] + cur
                else:
                    continue
                segs.pop(i)
                changed = True
                break
        if cur[0] == cur[-1] and len(cur) >= 4:
            rings.append(cur)
    return rings


def properties(osm_type: str, osm_id: int, tags: dict) -> dict:
    levels = _num(tags.get("building:levels"))
    height = _num(tags.get("height"))
    if levels is not None and levels >= 1:
        storeys, method = int(round(levels)), "building:levels"
    elif height is not None and height > 0:
        storeys, method = max(1, int(round(height / STOREY_HEIGHT_M))), "height/3.3"
    else:
        storeys, method = None, None
    hn, st = tags.get("addr:housenumber"), tags.get("addr:street")
    address = f"{hn} {st}" if hn and st else (st or None)
    btype = tags.get("building")
    return {
        "id": f"osm:{osm_type}/{osm_id}",
        "name": tags.get("name"),
        "address": address,
        "storeys": storeys,
        "storeys_method": method,
        "height_m": height,
        "year": _year(tags.get("start_date")),
        "material": tags.get("building:material"),
        "use": tags.get("building:use") or (btype if btype not in (None, "yes") else None),
        "building": btype,
        "tags": {k: tags[k] for k in TAGS_KEPT if k in tags},
        "synthetic": False,
    }


def to_geojson(osm: dict) -> dict:
    nodes = {e["id"]: (e["lon"], e["lat"]) for e in osm["elements"] if e["type"] == "node"}
    ways = {e["id"]: e for e in osm["elements"] if e["type"] == "way"}
    rel_member_ways: set[int] = set()
    feats = []
    for e in osm["elements"]:
        if e["type"] != "relation" or "building" not in e.get("tags", {}):
            continue
        outers = [ways[m["ref"]]["nodes"] for m in e.get("members", [])
                  if m["type"] == "way" and m.get("role") in ("outer", "") and m["ref"] in ways]
        inners = [ways[m["ref"]]["nodes"] for m in e.get("members", [])
                  if m["type"] == "way" and m.get("role") == "inner" and m["ref"] in ways]
        rings = _assemble_rings(outers)
        if not rings:
            continue
        try:
            polys = [[[list(nodes[n]) for n in r]] for r in rings]
            holes = [[list(nodes[n]) for n in r] for r in _assemble_rings(inners)]
        except KeyError:
            continue
        if len(polys) == 1:
            geom = {"type": "Polygon", "coordinates": polys[0] + holes}
        else:
            geom = {"type": "MultiPolygon", "coordinates": polys}
        for m in e.get("members", []):
            if m["type"] == "way":
                rel_member_ways.add(m["ref"])
        feats.append({"type": "Feature", "geometry": geom,
                      "properties": properties("relation", e["id"], e["tags"])})
    for wid, w in ways.items():
        tags = w.get("tags", {})
        # untagged ways are relation members only; tagged outer ways are covered by the relation
        if "building" not in tags or wid in rel_member_ways:
            continue
        nd = w.get("nodes", [])
        if len(nd) < 4 or nd[0] != nd[-1]:
            continue
        try:
            ring = [list(nodes[n]) for n in nd]
        except KeyError:
            continue
        feats.append({"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [ring]},
                      "properties": properties("way", wid, tags)})
    return {"type": "FeatureCollection", "synthetic": False, "source": "OpenStreetMap via Overpass",
            "licence": "ODbL 1.0, (c) OpenStreetMap contributors",
            "fetched": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
            "bbox": [BBOX["west"], BBOX["south"], BBOX["east"], BBOX["north"]], "features": feats}


def synthetic_grid(b: dict, nx: int = 14, ny: int = 12) -> dict:
    """Clearly labelled synthetic footprints on a regular grid. Not real buildings."""
    feats = []
    lat0 = (b["south"] + b["north"]) / 2
    dlat = (b["north"] - b["south"]) / ny
    dlon = (b["east"] - b["west"]) / nx
    m_per_deg_lat = 111_320.0
    m_per_deg_lon = 111_320.0 * math.cos(math.radians(lat0))
    k = 0
    for iy in range(ny):
        for ix in range(nx):
            k += 1
            w = min(0.7 * dlon, 30 / m_per_deg_lon + (k % 5) * 6 / m_per_deg_lon)
            h = min(0.7 * dlat, 25 / m_per_deg_lat + (k % 3) * 8 / m_per_deg_lat)
            x0 = b["west"] + (ix + 0.15) * dlon
            y0 = b["south"] + (iy + 0.15) * dlat
            ring = [[x0, y0], [x0 + w, y0], [x0 + w, y0 + h], [x0, y0 + h], [x0, y0]]
            storeys = [2, 3, 4, 6, 8, 12, 20, 30][(k * 7) % 8]
            feats.append({"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [ring]},
                          "properties": {"id": f"synthetic:{k}", "name": None,
                                         "address": f"{100 + k} Synthetic Street",
                                         "storeys": storeys, "storeys_method": "synthetic",
                                         "height_m": None, "year": None, "material": None,
                                         "use": None, "building": "yes", "tags": {},
                                         "synthetic": True}})
    return {"type": "FeatureCollection", "synthetic": True,
            "source": "SYNTHETIC grid (Overpass unreachable); not real buildings",
            "bbox": [b["west"], b["south"], b["east"], b["north"]], "features": feats}


ATTRIB_TEXT = """# Attribution

`footprints.geojson` contains building footprints and tags from OpenStreetMap.

Data (c) OpenStreetMap contributors. Available under the Open Database Licence (ODbL 1.0):
https://opendatacommons.org/licenses/odbl/1-0/ . See https://www.openstreetmap.org/copyright .

Any derived database that is publicly used must be offered under the ODbL as well.

Fetched {fetched} from the Overpass API (https://overpass-api.de) for bbox
south 37.7860, west -122.4050, north 37.7960, east -122.3920 (downtown San Francisco),
by `experiments/fetch_footprints.py`. Storeys come from `building:levels`, else `height / 3.3`,
else they are left empty.
"""

SYNTH_TEXT = """# Attribution

`footprints.geojson` is a SYNTHETIC grid written on {fetched} because the Overpass API could not be
reached. It contains no OpenStreetMap data and no real buildings. Every feature has
`properties.synthetic = true`. Re-run `python experiments/fetch_footprints.py` with network access
to replace it with real OpenStreetMap footprints (ODbL 1.0, (c) OpenStreetMap contributors).
"""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--synthetic", action="store_true", help="skip the network, write a grid")
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args(argv)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    gj = None
    if not a.synthetic:
        try:
            gj = to_geojson(fetch(BBOX))
        except Exception as exc:  # one request only; fall back rather than retry
            print(f"Overpass unreachable or failed ({type(exc).__name__}: {exc}); "
                  f"writing a SYNTHETIC grid instead.", file=sys.stderr)
    if gj is None:
        gj = synthetic_grid(BBOX)
        (a.out.parent / "ATTRIBUTION.md").write_text(SYNTH_TEXT.format(fetched=today), "utf-8")
    else:
        (a.out.parent / "ATTRIBUTION.md").write_text(ATTRIB_TEXT.format(fetched=gj["fetched"]),
                                                     "utf-8")
    a.out.write_text(json.dumps(gj, separators=(",", ":")), "utf-8")
    p = [f["properties"] for f in gj["features"]]
    print(f"wrote {a.out}: {len(p)} footprints, synthetic={gj['synthetic']}, "
          f"with storeys={sum(x['storeys'] is not None for x in p)}, "
          f"with building:levels={sum(x['storeys_method'] == 'building:levels' for x in p)}, "
          f"with height={sum(x['height_m'] is not None for x in p)}, "
          f"with year={sum(x['year'] is not None for x in p)}, "
          f"with address={sum(x['address'] is not None for x in p)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
