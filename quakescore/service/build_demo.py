"""One command to (re)build the demo database and the static dashboard data.

    python -m quakescore.service.build_demo                 # real results if present, else FIXTURE
    python -m quakescore.service.build_demo --fixture       # force FIXTURE records

Steps: load data/demo_city/footprints.geojson; load results/demo_city/buildings.json if it exists
(replacing any stored records), otherwise generate FIXTURE records; export dashboard/data.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from quakescore.service import export_static, fixtures, load_footprints, load_results
from quakescore.service.config import REPO, get_config
from quakescore.service.store import open_store

FOOTPRINTS = REPO / "data" / "demo_city" / "footprints.geojson"
REAL_RESULTS = REPO / "results" / "demo_city" / "buildings.json"
DASHBOARD_DATA = REPO / "dashboard" / "data"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--fixture", action="store_true", help="use FIXTURE records even if real ones exist")
    ap.add_argument("--results", type=Path, default=REAL_RESULTS)
    ap.add_argument("--out", type=Path, default=DASHBOARD_DATA)
    ap.add_argument("--db")
    a = ap.parse_args(argv)
    if a.db:
        os.environ["QS_DB"] = a.db
    cfg = get_config()
    store = open_store(cfg)
    gj = json.loads(FOOTPRINTS.read_text("utf-8"))
    ok, _ = load_footprints.load(store, gj)
    if a.results.exists() and not a.fixture:
        recs = json.loads(a.results.read_text("utf-8"))
        source = str(a.results)
    else:
        recs = fixtures.make_records(gj)
        source = "FIXTURE records (fabricated placeholders, quakescore/service/fixtures.py)"
    rep = load_results.load(store, recs, replace=True)
    meta = export_static.export(store, cfg, a.out)
    print(f"footprints: {ok}; results from {source}: loaded {rep['loaded']} {rep['provenance']}, "
          f"rejected {rep['rejected']}; exported {meta['buildings']} buildings to {a.out}, "
          f"status {meta['status']}")
    return 0 if rep["rejected"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
