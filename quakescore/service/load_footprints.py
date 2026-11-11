"""Load building footprints (GeoJSON FeatureCollection) into the store.

    python -m quakescore.service.load_footprints data/demo_city/footprints.geojson [--db PATH]

Each feature needs properties.id (e.g. "osm:way/123") and a Polygon or MultiPolygon geometry.
Attributes kept: storeys, height_m, year, material, use, name, address, synthetic, storeys_method.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from quakescore.service.store import open_store

ATTR_KEYS = ("storeys", "height_m", "year", "material", "use", "name", "address", "synthetic",
             "storeys_method")


def load(store, gj: dict) -> tuple[int, int]:
    ok = skipped = 0
    for f in gj.get("features", []):
        p = f.get("properties") or {}
        g = f.get("geometry") or {}
        if not p.get("id") or g.get("type") not in ("Polygon", "MultiPolygon"):
            skipped += 1
            continue
        attrs = {k: p.get(k) for k in ATTR_KEYS}
        if gj.get("synthetic"):
            attrs["synthetic"] = True
        store.upsert_building(p["id"], g, attrs)
        ok += 1
    store.set_meta("footprints_synthetic", "1" if gj.get("synthetic") else "0")
    return ok, skipped


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Load GeoJSON footprints into the QuakeScore store")
    ap.add_argument("geojson", type=Path)
    ap.add_argument("--db", help="SQLite path (default QS_DB or data/quakescore.sqlite)")
    a = ap.parse_args(argv)
    if a.db:
        os.environ["QS_DB"] = a.db
    store = open_store()
    ok, skipped = load(store, json.loads(a.geojson.read_text("utf-8")))
    print(f"loaded {ok} footprints ({skipped} skipped) into {store.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
