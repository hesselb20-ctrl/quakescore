"""Export the gated data as static files for the dashboard.

    python -m quakescore.service.export_static dashboard/data [--db PATH]

Writes
  buildings.geojson     every building, footprint + flat summary properties (released values only
                        for released buildings)
  b/<file>.json         per-building detail: exactly what GET /v1/buildings/{id} returns
  meta.json             generation date, provenance counts, K-threshold, bbox, attribution

The export goes through the same K-threshold gate as the API, so a static site never contains
parameters of sub-threshold buildings.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from quakescore.service import views
from quakescore.service.config import get_config
from quakescore.service.store import open_store


def detail_filename(bid: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", bid) + ".json"


def export(store, cfg, out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    bdir = out / "b"
    if bdir.exists():
        shutil.rmtree(bdir)
    bdir.mkdir()
    pairs = views.views_for(store, store.all_buildings(), cfg)
    fc = views.collection(pairs)
    for f, (_, v) in zip(fc["features"], pairs):
        f["properties"]["file"] = detail_filename(v["building_id"])
        (bdir / f["properties"]["file"]).write_text(json.dumps(v, separators=(",", ":")), "utf-8")
    (out / "buildings.geojson").write_text(json.dumps(fc, separators=(",", ":")), "utf-8")
    provs: dict[str, int] = {}
    status: dict[str, int] = {}
    for _, v in pairs:
        provs[v["provenance"] or "NONE"] = provs.get(v["provenance"] or "NONE", 0) + 1
        status[v["coverage"]["status"]] = status.get(v["coverage"]["status"], 0) + 1
    xs = [b["lon"] for b, _ in pairs]
    ys = [b["lat"] for b, _ in pairs]
    meta = {"generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
            "buildings": len(pairs), "provenance": provs, "status": status,
            "k_threshold": {"contributors": cfg.k_contributors, "sessions": cfg.k_sessions},
            "bbox": [min(xs), min(ys), max(xs), max(ys)] if pairs else None,
            "footprints_synthetic": store.get_meta("footprints_synthetic") == "1",
            "attribution": "Building footprints (c) OpenStreetMap contributors, ODbL 1.0"}
    (out / "meta.json").write_text(json.dumps(meta, indent=1), "utf-8")
    return meta


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Export static dashboard data")
    ap.add_argument("out", type=Path)
    ap.add_argument("--db")
    a = ap.parse_args(argv)
    if a.db:
        os.environ["QS_DB"] = a.db
    cfg = get_config()
    meta = export(open_store(cfg), cfg, a.out)
    print(f"exported {meta['buildings']} buildings to {a.out} (provenance {meta['provenance']}, "
          f"status {meta['status']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
