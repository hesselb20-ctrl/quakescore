"""Portfolio matching: a buyer's CSV of assets -> QuakeScore buildings.

Accepted columns (case-insensitive, any subset): building_id; lat, lon (aliases latitude,
longitude, lng); address; plus an optional ref / id / name column that is echoed back.

Matching order per row:
  1. building_id   exact match on the stored id
  2. lat/lon       point-in-polygon; else the nearest footprint whose edge is within 30 m
  3. address       normalised string match against footprint address tags (addr:housenumber +
                   addr:street); several buildings with the same address -> "ambiguous"
  4. geocoder      plug-in point, off in v1: set GEOCODER to a callable(address) -> (lat, lon) | None
                   and unmatched addresses are geocoded and then matched as in step 2.

There is no external geocoder in v1, so addresses only match buildings whose OSM footprint carries
address tags.
"""
from __future__ import annotations

import csv
import io
import math
import re
from typing import Callable

from quakescore.service import geo
from quakescore.service.config import Config
from quakescore.service.coverage import building_view, live_cov

NEAREST_M = 30.0
MAX_ROWS = 10_000

GEOCODER: Callable[[str], tuple[float, float] | None] | None = None   # plug-in point (v1: none)

ABBREV = {"st": "street", "str": "street", "ave": "avenue", "av": "avenue", "blvd": "boulevard",
          "rd": "road", "dr": "drive", "ln": "lane", "ct": "court", "pl": "place", "sq": "square",
          "ter": "terrace", "hwy": "highway", "pkwy": "parkway", "aly": "alley", "cir": "circle",
          "n": "north", "s": "south", "e": "east", "w": "west", "ne": "northeast",
          "nw": "northwest", "se": "southeast", "sw": "southwest", "1st": "first", "2nd": "second",
          "3rd": "third", "4th": "fourth", "5th": "fifth", "6th": "sixth", "7th": "seventh",
          "8th": "eighth", "9th": "ninth", "10th": "tenth"}

ALIASES = {"building_id": ("building_id", "buildingid", "quakescore_id"),
           "lat": ("lat", "latitude", "y"), "lon": ("lon", "lng", "long", "longitude", "x"),
           "address": ("address", "addr", "street_address"),
           "ref": ("ref", "asset_id", "id", "name", "reference")}


def normalise_address(s: str | None) -> str | None:
    """'1 Market St., San Francisco, CA' -> '1 market street'. Only the part before the first
    comma is used, because footprint tags carry house number and street only."""
    if not s:
        return None
    s = s.split(",")[0].lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    toks = [ABBREV.get(t, t) for t in s.split()]
    return " ".join(toks) or None


def _col(header: list[str], key: str) -> int | None:
    h = [c.strip().lower().replace(" ", "_") for c in header]
    for alias in ALIASES[key]:
        if alias in h:
            return h.index(alias)
    return None


def parse_csv(text: str) -> list[dict]:
    rows = list(csv.reader(io.StringIO(text.lstrip("﻿"))))
    if not rows:
        raise ValueError("empty CSV")
    header, body = rows[0], [r for r in rows[1:] if any(c.strip() for c in r)]
    idx = {k: _col(header, k) for k in ALIASES}
    if idx["ref"] == idx["building_id"]:
        idx["ref"] = None
    if idx["building_id"] is None and idx["address"] is None and (idx["lat"] is None or idx["lon"] is None):
        raise ValueError("CSV needs a building_id column, lat and lon columns, or an address column")
    if len(body) > MAX_ROWS:
        raise ValueError(f"at most {MAX_ROWS} rows per upload")
    out = []
    for r in body:
        def g(k):
            i = idx[k]
            return r[i].strip() if i is not None and i < len(r) and r[i].strip() else None
        out.append({k: g(k) for k in ALIASES})
    return out


class Matcher:
    def __init__(self, store, cfg: Config):
        self.store = store
        self.cfg = cfg
        self._addr: dict[str, list[str]] | None = None

    def _address_index(self) -> dict[str, list[str]]:
        if self._addr is None:
            self._addr = {}
            for b in self.store.all_buildings():
                n = normalise_address(b["attrs"].get("address"))
                if n:
                    self._addr.setdefault(n, []).append(b["id"])
        return self._addr

    def by_point(self, lat: float, lon: float) -> tuple[str | None, str | None, float | None]:
        cands = self.store.buildings_in_bbox(*geo.expand_bbox(lat, lon, NEAREST_M + 5))
        inside = [b for b in cands if b["footprint"] and geo.contains(b["footprint"], lat, lon)]
        if inside:
            # nested footprints (building:part style): prefer the smallest containing one
            inside.sort(key=lambda b: (geo.bbox(b["footprint"])[2] - geo.bbox(b["footprint"])[0]) *
                        (geo.bbox(b["footprint"])[3] - geo.bbox(b["footprint"])[1]))
            return inside[0]["id"], "point_in_polygon", 0.0
        best, best_d = None, math.inf
        for b in cands:
            d = geo.distance_m(b["footprint"] or {"type": "Point", "coordinates": [b["lon"], b["lat"]]},
                               lat, lon)
            if d < best_d:
                best, best_d = b, d
        if best is not None and best_d <= NEAREST_M:
            return best["id"], "nearest_footprint", round(best_d, 1)
        return None, None, None

    def match_row(self, row: dict) -> dict:
        res = {"building_id": None, "match_status": "unmatched", "match_method": None,
               "distance_m": None, "note": None}
        bid = row.get("building_id")
        if bid and self.store.get_building(bid):
            res.update(building_id=bid, match_status="matched", match_method="building_id")
            return res
        notes = []
        if bid:
            notes.append("building_id not found")
        lat_s, lon_s = row.get("lat"), row.get("lon")
        if lat_s is not None and lon_s is not None:
            try:
                lat, lon = float(lat_s), float(lon_s)
                if not (-90 <= lat <= 90 and -180 <= lon <= 180) or not (math.isfinite(lat) and math.isfinite(lon)):
                    raise ValueError
            except ValueError:
                notes.append("lat/lon not valid numbers")
            else:
                found, method, d = self.by_point(lat, lon)
                if found:
                    res.update(building_id=found, match_status="matched", match_method=method, distance_m=d)
                    res["note"] = "; ".join(notes) or None
                    return res
                notes.append(f"no footprint within {NEAREST_M:.0f} m")
        addr = normalise_address(row.get("address"))
        if addr:
            ids = self._address_index().get(addr, [])
            if len(ids) == 1:
                res.update(building_id=ids[0], match_status="matched", match_method="address")
                res["note"] = "; ".join(notes) or None
                return res
            if len(ids) > 1:
                res.update(match_status="ambiguous", candidates=ids[:10])
                notes.append(f"{len(ids)} footprints share this address")
                res["note"] = "; ".join(notes)
                return res
            if GEOCODER is not None:
                pt = GEOCODER(row["address"])
                if pt:
                    found, method, d = self.by_point(*pt)
                    if found:
                        res.update(building_id=found, match_status="matched",
                                   match_method=f"geocoded+{method}", distance_m=d)
                        return res
            notes.append("address not found in footprint address tags (no geocoder in v1)")
        if not (bid or addr or (lat_s and lon_s)):
            res["match_status"] = "invalid"
            notes.append("row has no building_id, lat/lon or address")
        res["note"] = "; ".join(notes) or None
        return res


def _pct(vals: list[float], q: float) -> float | None:
    if not vals:
        return None
    v = sorted(vals)
    pos = (len(v) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    return round(v[lo] + (v[hi] - v[lo]) * (pos - lo), 1)


def run(store, cfg: Config, text: str) -> dict:
    rows = parse_csv(text)
    m = Matcher(store, cfg)
    ids = []
    out = []
    for i, r in enumerate(rows, 1):
        res = m.match_row(r)
        out.append({"row": i, "ref": r.get("ref"), **res})
        if res["building_id"]:
            ids.append(res["building_id"])
    recs = store.results_for(sorted(set(ids)))
    scores = []
    for o in out:
        bid = o["building_id"]
        if not bid:
            o.update(coverage_status=None, provenance=None, score=None, f1=None)
            continue
        b = store.get_building(bid)
        v = building_view(b, recs.get(bid), live_cov(store.session_rows(bid)), cfg,
                          store.needs_recompute(bid))
        o["coverage_status"] = v["coverage"]["status"]
        o["sessions_needed"] = v["coverage"]["sessions_needed"]
        o["provenance"] = v["provenance"]
        if v["released"]:
            s = v["score"]
            o["score"] = {"value": s["value"], "lo": s["lo"], "hi": s["hi"]}
            o["f1"] = (None if v.get("f1") is None else
                       {"value": v["f1"], "lo": v.get("f1_lo"), "hi": v.get("f1_hi")})
            scores.append(float(s["value"]))
        else:
            o["score"] = None
            o["f1"] = None
    n = len(out)
    matched = sum(o["match_status"] == "matched" for o in out)
    scored = sum(o["score"] is not None for o in out)
    edges = [0, 20, 40, 60, 80, 100]
    hist = [{"lo": edges[i], "hi": edges[i + 1],
             "count": sum(edges[i] <= s < edges[i + 1] or (i == 4 and s == 100) for s in scores)}
            for i in range(5)]
    methods: dict[str, int] = {}
    for o in out:
        if o["match_method"]:
            methods[o["match_method"]] = methods.get(o["match_method"], 0) + 1
    provs: dict[str, int] = {}
    for o in out:
        if o.get("provenance"):
            provs[o["provenance"]] = provs.get(o["provenance"], 0) + 1
    summary = {
        "rows": n, "matched": matched, "unmatched": sum(o["match_status"] == "unmatched" for o in out),
        "ambiguous": sum(o["match_status"] == "ambiguous" for o in out),
        "invalid": sum(o["match_status"] == "invalid" for o in out),
        "scored": scored,
        "coverage_pct": round(100 * scored / matched, 1) if matched else 0.0,
        "coverage_pct_of_rows": round(100 * scored / n, 1) if n else 0.0,
        "match_methods": methods, "provenance": provs,
        "score_distribution": {"bins": hist, "median": _pct(scores, 0.5), "p10": _pct(scores, 0.1),
                               "p90": _pct(scores, 0.9), "n": len(scores),
                               "note": "scores of released buildings only; each has its own band"},
        "geocoder": None if GEOCODER is None else getattr(GEOCODER, "__name__", "custom"),
    }
    return {"summary": summary, "rows": out}
