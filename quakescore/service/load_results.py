"""Load batch result records (a JSON list in the schema of docs/api.md) into the store.

    python -m quakescore.service.load_results results/demo_city/buildings.json [--replace] [--db PATH]

--replace deletes every stored record first (use it when swapping FIXTURE records for real batch
output). Invalid records are reported and skipped; they are never served. Buildings that have a
record but no stored footprint are added as points at attrs.lat / attrs.lon.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from quakescore.service.coverage import RecordError, validate_record
from quakescore.service.store import open_store


def load(store, records: list[dict], replace: bool = False) -> dict:
    if not isinstance(records, list):
        raise ValueError("results file must contain a JSON list of records")
    if replace:
        store.clear_results()
    ok, errors, added_points = 0, [], 0
    provs: dict[str, int] = {}
    for rec in records:
        try:
            validate_record(rec)
        except RecordError as e:
            errors.append(str(e))
            continue
        if store.get_building(rec["building_id"]) is None:
            a = rec["attrs"]
            store.upsert_building(rec["building_id"], None,
                                  {k: a.get(k) for k in ("storeys", "height_m", "year", "material",
                                                         "use", "name", "address")},
                                  lat=a["lat"], lon=a["lon"])
            added_points += 1
        store.put_result(rec)
        provs[rec["provenance"]] = provs.get(rec["provenance"], 0) + 1
        ok += 1
    return {"loaded": ok, "rejected": len(errors), "errors": errors[:20], "provenance": provs,
            "buildings_added_as_points": added_points}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Load QuakeScore result records")
    ap.add_argument("path", type=Path)
    ap.add_argument("--replace", action="store_true", help="delete existing records first")
    ap.add_argument("--db")
    a = ap.parse_args(argv)
    if a.db:
        os.environ["QS_DB"] = a.db
    store = open_store()
    rep = load(store, json.loads(a.path.read_text("utf-8")), replace=a.replace)
    print(f"loaded {rep['loaded']} records {rep['provenance']}, rejected {rep['rejected']}, "
          f"added {rep['buildings_added_as_points']} buildings as points, into {store.path}")
    for e in rep["errors"]:
        print("  rejected:", e)
    return 0 if rep["rejected"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
