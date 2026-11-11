"""Demo city: real OpenStreetMap footprints, SIMULATED buildings, contributors and sessions.

Footprints and tags are real (data/demo_city/footprints.geojson, OpenStreetMap contributors, ODbL).
Everything else is simulated and labelled SIM: each footprint gets a hidden "true" structure drawn
from the class model, a number of contributing phones from an assumed adoption rate, and sessions
generated with the fast spectral path. The normal batch pipeline then produces the records.

Assumptions (ASSUMED, stated so they can be challenged):
  adoption        one contributing phone per 1500 m^2 of floor area
  sessions        geometric, mean 12 nights per contributor
  phone mix       30% low-noise, 50% mid, 20% high-noise
  nights          30% quiet, 50% typical, 20% energetic
  anomalies       4% of buildings have 30-55% of the expected stiffness
  damage          3% of scored buildings lose 12% stiffness in month 7 of the drift series
"""
from __future__ import annotations

import json
import sys

import numpy as np

from common import RESULTS, ROOT, bands_for, run_pool, save, seed_of
from quakescore.product import building_record
from quakescore.sim.building import Building
from quakescore.sim.excitation import ENVIRONMENTS
from quakescore.sim.fast import FastSite, simulate_features
from quakescore.sim.phone import PHONE_MODELS, random_placement
from quakescore.vuln.score import SIGMA_LN_T, Attributes, class_prior, expected_period

ADOPTION_M2 = 1500.0
MAX_SESSIONS = 120
UPDATED = "2026-11-11"


def _area_centroid(geom: dict) -> tuple[float, float, float]:
    ring = geom["coordinates"][0] if geom["type"] == "Polygon" else geom["coordinates"][0][0]
    xy = np.array(ring, float)
    lon0, lat0 = xy[:, 0].mean(), xy[:, 1].mean()
    x = (xy[:, 0] - lon0) * 111320.0 * np.cos(np.radians(lat0))
    y = (xy[:, 1] - lat0) * 110540.0
    area = 0.5 * abs(np.dot(x[:-1], y[1:]) - np.dot(x[1:], y[:-1]))
    return float(area), float(lat0), float(lon0)


def _one(task):
    feat, seed = task
    rng = np.random.default_rng(seed)
    pr = feat["properties"]
    area, lat, lon = _area_centroid(feat["geometry"])
    attrs = {"storeys": pr.get("storeys"), "height_m": pr.get("height_m"), "year": pr.get("year"),
             "material": pr.get("material"), "use": pr.get("use"), "lat": lat, "lon": lon,
             "name": pr.get("name"), "address": pr.get("address")}
    truth = {"building_id": pr["id"], "simulated": False}
    if not attrs["storeys"]:
        attrs["storeys"] = max(1, round((attrs["height_m"] or 0) / 3.3)) or None
    if not attrs["storeys"]:
        rec = building_record(pr["id"], {**attrs, "storeys": 2}, [], rng=rng, updated=UPDATED)
        rec["attrs"]["storeys"] = None
        rec["prior"] = None
        return rec, truth
    n = int(min(attrs["storeys"], 60))
    height = float(attrs["height_m"] or 3.3 * n)
    a = Attributes(height_m=height, storeys=n, year=attrs["year"], material=attrs["material"])
    prior = class_prior(a)
    cls = str(rng.choice(list(prior), p=list(prior.values())))
    k_ratio = float(rng.uniform(0.30, 0.55)) if rng.random() < 0.04 else 1.0
    t1 = expected_period(cls, height) * float(np.exp(rng.normal(0, SIGMA_LN_T))) / np.sqrt(k_ratio)
    f1 = 1.0 / t1
    zeta = float(np.clip(min(0.0143 * f1, 0.05) * np.exp(rng.normal(0, 0.3)), 0.006, 0.06))
    side = float(np.clip(np.sqrt(max(area, 60.0)), 8.0, 80.0))
    b = Building(n, (f1, f1 * rng.uniform(1.08, 1.30), f1 * rng.uniform(1.3, 1.65)), (zeta, zeta, zeta),
                 storey_height=height / n, width=(side, side), building_id=pr["id"])
    n_contrib = int(min(rng.poisson(area * n / ADOPTION_M2), 40))
    sessions, sites = [], {}
    bands = bands_for([b.modes["x"].f[0], b.modes["y"].f[0]])
    plan = []
    for c in range(n_contrib):
        model = PHONE_MODELS[str(rng.choice(["low", "mid", "high"], p=[0.3, 0.5, 0.2]))]
        floor = int(rng.integers(1, n + 1))
        plan += [(c, model, floor)] * int(min(rng.geometric(1 / 12.0), 40))
    if len(plan) > MAX_SESSIONS:
        plan = [plan[i] for i in sorted(rng.choice(len(plan), MAX_SESSIONS, replace=False))]
    for j, (c, model, floor) in enumerate(plan):
        env_name = str(rng.choice(["quiet", "typical", "energetic"], p=[0.3, 0.5, 0.2]))
        key = (floor, env_name)
        if key not in sites:
            sites[key] = FastSite(b, ENVIRONMENTS[env_name], floor, (0.0, 0.0), bands)
        p = random_placement(rng, model, floor, contributor=f"{c:02d}")
        p.pos = (0.0, 0.0)
        sessions.append(simulate_features(b, ENVIRONMENTS[env_name], p, 6 * 3600.0, 1.79e9 - 86400.0 * (j % 90), rng,
                                          session_id=f"{pr['id']}-{j}", site=sites[key], bands=bands))
    rec = building_record(pr["id"], attrs, sessions, rng=rng, updated=UPDATED)
    truth.update(simulated=True, cls=cls, f1=f1, zeta=zeta, k_ratio=k_ratio, contributors=n_contrib,
                 sessions=len(sessions), storeys=n, damage=False)
    if rec["coverage"]["status"] == "scored":
        damaged = bool(rng.random() < 0.03)
        days = np.arange(12) * 30.0
        temp = 14 + 4 * np.sin(2 * np.pi * (days - 120) / 365.25) + rng.normal(0, 1.5, 12)
        sig = max((rec["f1_hi"] - rec["f1_lo"]) / 3.29, 0.001 * rec["f1"]) * np.sqrt(3.0)
        slow = np.zeros(12)
        for i in range(1, 12):
            slow[i] = 0.7 * slow[i - 1] + rng.normal(0, 0.003 * np.sqrt(0.51))
        fser = rec["f1"] * (1 - 5e-4 * (temp - 14)) * (1 + slow) * np.where((days >= 180) & damaged, np.sqrt(0.88), 1.0)
        fser = fser + rng.normal(0, sig, 12)
        history = [(float(d), float(v), float(sig), float(tc)) for d, v, tc in zip(days, fser, temp)]
        rec2 = building_record(pr["id"], attrs, sessions, history=history, rng=np.random.default_rng(seed), updated=UPDATED, n_boot=0)
        rec["drift"] = rec2["drift"]
        truth["damage"] = damaged
    return rec, truth


def main() -> None:
    feats = json.loads((ROOT / "data" / "demo_city" / "footprints.geojson").read_text(encoding="utf-8"))["features"]
    if "--limit" in sys.argv:
        feats = feats[: int(sys.argv[sys.argv.index("--limit") + 1])]
    out = run_pool(_one, [(f, seed_of("demo", f["properties"]["id"])) for f in feats], label="demo city",
                   checkpoint=None if "--limit" in sys.argv else "demo_city")
    recs, truth = [r for r, _ in out], [t for _, t in out]
    (RESULTS / "demo_city").mkdir(parents=True, exist_ok=True)
    (RESULTS / "demo_city" / "buildings.json").write_text(json.dumps(recs))
    tmap = {t["building_id"]: t for t in truth}
    scored = [r for r in recs if r["coverage"]["status"] == "scored"]
    ferr = [abs(r["f1"] / tmap[r["building_id"]]["f1"] - 1) for r in scored]
    xy_confused = [r for r in scored if abs(r["f1"] / tmap[r["building_id"]]["f1"] - 1) > 0.05]
    anomalous = [t for t in truth if t.get("simulated") and t["k_ratio"] < 1]
    flagged = [r for r in scored if r["stiffness"] and r["stiffness"]["flag"]]
    damaged = [r for r in scored if tmap[r["building_id"]].get("damage")]
    alerts = [r for r in scored if r["drift"] and r["drift"]["alert"]]
    by_height = {}
    for lo, hi, name in ((1, 3, "1-3"), (4, 7, "4-7"), (8, 14, "8-14"), (15, 29, "15-29"), (30, 999, "30+")):
        grp = [r for r in recs if r["attrs"]["storeys"] and lo <= r["attrs"]["storeys"] <= hi]
        by_height[name] = {"buildings": len(grp), "with_sessions": sum(r["coverage"]["sessions"] > 0 for r in grp),
                           "scored": sum(r["coverage"]["status"] == "scored" for r in grp)}
    summary = {
        "provenance": "SIM (footprints REAL, from OpenStreetMap)", "footprints": len(recs),
        "with_storeys": sum(1 for r in recs if r["attrs"]["storeys"]),
        "status": {s: sum(r["coverage"]["status"] == s for r in recs) for s in ("scored", "needs_data", "no_data")},
        "sessions_total": sum(r["coverage"]["sessions"] for r in recs), "by_storeys": by_height,
        "f1_abs_error_median": float(np.median(ferr)) if ferr else None,
        "f1_abs_error_p90": float(np.percentile(ferr, 90)) if ferr else None,
        "f1_within_5pct": float(np.mean(np.array(ferr) <= 0.05)) if ferr else None,
        "f1_wrong_mode": len(xy_confused),
        "anomalous_buildings": len(anomalous),
        "anomalous_scored": sum(1 for r in scored if tmap[r["building_id"]]["k_ratio"] < 1),
        "anomaly_flags": len(flagged), "anomaly_flags_correct": sum(1 for r in flagged if tmap[r["building_id"]]["k_ratio"] < 1),
        "damaged_scored": len(damaged), "drift_alerts": len(alerts),
        "drift_alerts_correct": sum(1 for r in alerts if tmap[r["building_id"]].get("damage")),
        "score_median": float(np.median([r["score"]["value"] for r in scored])) if scored else None,
        "score_band_median_width": float(np.median([r["score"]["hi"] - r["score"]["lo"] for r in scored])) if scored else None,
        "prior_band_median_width": float(np.median([r["score"]["prior_hi"] - r["score"]["prior_lo"] for r in scored])) if scored else None,
    }
    save("demo_city/summary.json", summary)
    save("demo_city/truth.json", truth)
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
