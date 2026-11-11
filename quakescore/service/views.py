"""Bulk view helpers shared by the API and the static export. All go through coverage.building_view."""
from __future__ import annotations

import csv
import io

from quakescore.service.config import Config
from quakescore.service.coverage import building_view, live_cov, summary_properties

ZERO = {"sessions": 0, "contributors": 0, "floors": 0}


def view_one(store, bid: str, cfg: Config) -> dict | None:
    b = store.get_building(bid)
    rec = store.get_result(bid)
    if b is None and rec is None:
        return None
    return building_view(b, rec, live_cov(store.session_rows(bid)), cfg, store.needs_recompute(bid))


def views_for(store, buildings: list[dict], cfg: Config) -> list[tuple[dict, dict]]:
    recs = store.results_for([b["id"] for b in buildings])
    counts = store.session_counts()
    stale = store.recompute_ids()
    return [(b, building_view(b, recs.get(b["id"]), counts.get(b["id"], ZERO), cfg, b["id"] in stale))
            for b in buildings]


def geometry(b: dict) -> dict:
    return b["footprint"] or {"type": "Point", "coordinates": [b["lon"], b["lat"]]}


def feature(b: dict, v: dict) -> dict:
    return {"type": "Feature", "id": v["building_id"], "geometry": geometry(b),
            "properties": summary_properties(v)}


def collection(pairs, meta: dict | None = None) -> dict:
    fc = {"type": "FeatureCollection", "features": [feature(b, v) for b, v in pairs]}
    if meta:
        fc["meta"] = meta
    return fc


EXPORT_COLUMNS = ["building_id", "provenance", "updated", "lat", "lon", "name", "address", "storeys",
                  "score", "score_lo", "score_hi", "prior_score", "prior_lo", "prior_hi", "f1_hz",
                  "f1_lo_hz", "f1_hi_hz", "zeta1", "zeta1_lo", "zeta1_hi", "class_map",
                  "gem_taxonomy", "k_ratio", "stiffness_z", "stiffness_flag", "drift_pct_per_year",
                  "drift_alert", "sessions", "contributors", "floors"]


def export_row(v: dict) -> dict:
    s, st, dr, a, c = v["score"], v.get("stiffness") or {}, v.get("drift") or {}, v["attrs"], v["coverage"]
    return {"building_id": v["building_id"], "provenance": v["provenance"], "updated": v["updated"],
            "lat": round(a["lat"], 6), "lon": round(a["lon"], 6), "name": a.get("name"),
            "address": a.get("address"), "storeys": a.get("storeys"), "score": s["value"],
            "score_lo": s["lo"], "score_hi": s["hi"], "prior_score": s.get("prior_value"),
            "prior_lo": s.get("prior_lo"), "prior_hi": s.get("prior_hi"), "f1_hz": v.get("f1"),
            "f1_lo_hz": v.get("f1_lo"), "f1_hi_hz": v.get("f1_hi"), "zeta1": v.get("zeta1"),
            "zeta1_lo": v.get("zeta1_lo"), "zeta1_hi": v.get("zeta1_hi"),
            "class_map": v.get("class_map"), "gem_taxonomy": v.get("gem_taxonomy"),
            "k_ratio": st.get("k_ratio"), "stiffness_z": st.get("z"), "stiffness_flag": st.get("flag"),
            "drift_pct_per_year": dr.get("pct_per_year"), "drift_alert": dr.get("alert"),
            "sessions": c["sessions"], "contributors": c["contributors"], "floors": c["floors"]}


def export_csv(views: list[dict]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=EXPORT_COLUMNS, lineterminator="\n")
    w.writeheader()
    for v in views:
        if v["released"]:
            w.writerow(export_row(v))
    return buf.getvalue()
