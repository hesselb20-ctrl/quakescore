"""FIXTURE result records for the demo footprints.

These are fabricated placeholder records with provenance "FIXTURE". They exist only so that the API,
static export and dashboard can be built and tested before the batch job writes
results/demo_city/buildings.json. They are not measurements and not simulator output; the numbers
are drawn from simple illustrative distributions with a fixed seed. Every record says "FIXTURE", and
the dashboard labels it "Simulated data".

    python -m quakescore.service.fixtures data/demo_city/footprints.geojson out.json
"""
from __future__ import annotations

import json
import math
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np

from quakescore.service import geo

PERIOD_A = {"W1": 0.03125, "URM": 0.03125, "C1": 0.018, "C2": 0.013, "S1": 0.024, "S2": 0.020,
            "RM1": 0.013, "RM2": 0.013, "PC2": 0.013, "C3": 0.016}
GEM = {"C1": "CR/LFM", "C2": "CR/LWAL", "C3": "CR/LFINF", "S1": "S/LFM", "S2": "S/LFBR",
       "W1": "W/LWAL", "URM": "MUR/LWAL", "RM1": "MR/LWAL", "RM2": "MR/LWAL", "PC2": "CR+PC/LWAL"}
MIX = {"L": {"W1": 0.45, "RM1L": 0.15, "C2L": 0.12, "S1L": 0.10, "URML": 0.10, "C1L": 0.08},
       "M": {"C2M": 0.30, "S1M": 0.25, "C1M": 0.20, "S2M": 0.15, "RM2M": 0.10},
       "H": {"S1H": 0.40, "C2H": 0.35, "C1H": 0.25}}


def _family(cls: str) -> str:
    for k in sorted(PERIOD_A, key=len, reverse=True):
        if cls.startswith(k):
            return k
    return "C2"


def _hclass(storeys: int) -> str:
    return "L" if storeys <= 3 else ("M" if storeys <= 7 else "H")


def _round(x, n=3):
    return None if x is None else float(round(float(x), n))


def make_record(props: dict, lat: float, lon: float, rng: np.random.Generator, today: date) -> dict:
    storeys = props.get("storeys")
    st = storeys if storeys else int(rng.choice([2, 3, 4]))
    height = props.get("height_m") or st * 3.3
    u = rng.random()
    if u < 0.48:
        sessions = int(rng.integers(5, 60))
        contributors = int(rng.integers(3, max(4, sessions // 3)))
        status = "scored"
    elif u < 0.72:
        sessions = int(rng.integers(1, 7))
        contributors = int(rng.integers(1, min(sessions, 2) + 1))
        status = "needs_data"
    else:
        sessions = contributors = 0
        status = "no_data"
    floors = 0 if sessions == 0 else int(min(st, rng.integers(1, 6), sessions))
    rec = {
        "building_id": props["id"], "provenance": "FIXTURE", "updated": today.isoformat(),
        "attrs": {"storeys": storeys, "height_m": props.get("height_m"), "year": props.get("year"),
                  "material": props.get("material"), "use": props.get("use"), "lat": lat, "lon": lon,
                  "name": props.get("name"), "address": props.get("address")},
        "coverage": {"sessions": sessions, "contributors": contributors, "floors": floors,
                     "status": status,
                     "sessions_needed": None if status == "scored" else max(5 - sessions, 3 - contributors, 1)},
        "modes": [], "f1": None, "f1_lo": None, "f1_hi": None, "zeta1": None, "zeta1_lo": None,
        "zeta1_hi": None, "class_probs": None, "class_map": None, "gem_taxonomy": None,
        "stiffness": None, "score": None, "damage": None, "drift": None, "spectrum": None,
    }
    if sessions == 0:
        return rec

    # class distribution from the height class mix, sharpened by a random "measurement"
    mix = MIX[_hclass(st)]
    names = list(mix)
    p = np.array([mix[n] for n in names]) * rng.dirichlet(np.ones(len(names)) * 2.0)
    p /= p.sum()
    order = np.argsort(-p)[:4]
    probs = {names[i]: _round(p[i] / p[order].sum(), 2) for i in order}
    cmap = names[order[0]]
    fam = _family(cmap)
    t_exp = PERIOD_A[fam] * height if fam not in ("W1", "URM") else PERIOD_A[fam] * height ** 0.75
    k_ratio = float(np.exp(rng.normal(0.0, 0.18)))
    if rng.random() < 0.06:
        k_ratio *= float(rng.uniform(0.55, 0.75))          # a few anomalously soft buildings
    t_meas = t_exp / math.sqrt(k_ratio)
    f1 = 1.0 / t_meas
    rel = 0.25 / math.sqrt(sessions)                        # interval narrows with sessions
    f1_lo, f1_hi = f1 * (1 - 0.6 * rel), f1 * (1 + 0.6 * rel)
    z1 = float(np.clip(0.0143 * f1 + rng.normal(0, 0.004), 0.006, 0.06))
    z_lo, z_hi = z1 * (1 - 1.5 * rel), z1 * (1 + 2.0 * rel)
    zsc = float(math.log(k_ratio) / 0.25 * 0.5)
    modes = [{"f": _round(f1), "f_lo": _round(f1_lo), "f_hi": _round(f1_hi), "zeta": _round(z1, 4),
              "zeta_lo": _round(z_lo, 4), "zeta_hi": _round(z_hi, 4),
              "z": _round(rng.uniform(6, 25), 1), "label": "structural"}]
    f2 = f1 * float(rng.uniform(2.8, 3.3))
    if f2 < 18:
        modes.append({"f": _round(f2), "f_lo": _round(f2 * (1 - rel)), "f_hi": _round(f2 * (1 + rel)),
                      "zeta": _round(z1 * 1.2, 4), "zeta_lo": _round(z1 * 0.8, 4),
                      "zeta_hi": _round(z1 * 1.9, 4), "z": _round(rng.uniform(5, 12), 1),
                      "label": "structural"})
    if rng.random() < 0.5:
        ft = float(rng.choice([7.5, 9.8, 12.5, 14.9]))
        modes.append({"f": ft, "f_lo": _round(ft - 0.01), "f_hi": _round(ft + 0.01), "zeta": 0.0008,
                      "zeta_lo": 0.0004, "zeta_hi": 0.0012, "z": _round(rng.uniform(8, 30), 1),
                      "label": str(rng.choice(["rejected:tone", "rejected:fleet", "rejected:width"]))})

    base = 72 - 1.4 * st + 40 * (k_ratio - 1) + (8 if (props.get("year") or 1960) > 1980 else 0)
    if fam in ("URM",):
        base -= 25
    score = float(np.clip(base + rng.normal(0, 8), 4, 97))
    half = 6 + 40 * rel + rng.uniform(0, 4)
    prior = float(np.clip(base - 40 * (k_ratio - 1) + rng.normal(0, 4), 3, 97))
    prior_half = half * 1.9 + 6

    def dmg(level):
        sev = (100 - score) / 100 * level / 0.3
        ex = [1 - math.exp(-1.6 * sev * w) for w in (1.0, 0.55, 0.25, 0.09)]   # exceedance
        ex = [min(max(e, 0.0), 1.0) for e in ex]
        ds = [ex[0] - ex[1], ex[1] - ex[2], ex[2] - ex[3], ex[3]]                # in each state
        return dict(zip(("slight", "moderate", "extensive", "complete"), (_round(x, 3) for x in ds)))

    n_pts = int(rng.integers(6, 13))
    d0 = today - timedelta(days=30 * (n_pts - 1))
    drift_pct = float(rng.normal(-0.2, 0.6))
    alert = rng.random() < 0.05
    if alert:
        drift_pct = float(rng.uniform(-6, -3))
    series = []
    for i in range(n_pts):
        t = i / 12
        fi = f1 * (1 + drift_pct / 100 * (t - (n_pts - 1) / 12) + 0.004 * math.sin(2 * math.pi * t))
        series.append([(d0 + timedelta(days=30 * i)).isoformat(), _round(fi * (1 + rng.normal(0, 0.003)), 4),
                       _round(f1 * rel * 0.5, 4)])

    band = "L" if f1 < 1.0 else ("M" if f1 < 4.0 else "H")
    lo_f, hi_f = {"L": (0.08, 1.2), "M": (0.6, 4.7), "H": (2.5, 18.0)}[band]
    fgrid = np.geomspace(lo_f, hi_f, 160)
    exc = np.ones_like(fgrid) + rng.normal(0, 0.04, fgrid.size)
    for m in modes:
        if lo_f <= m["f"] <= hi_f:
            amp = (m["z"] or 8) / 6
            g = m["zeta"] if m["label"] == "structural" else 0.003
            exc += amp / (1 + ((fgrid - m["f"]) / (g * m["f"] * 2 + 1e-4)) ** 2)
    rec.update({
        "modes": modes, "f1": _round(f1), "f1_lo": _round(f1_lo), "f1_hi": _round(f1_hi),
        "zeta1": _round(z1, 4), "zeta1_lo": _round(z_lo, 4), "zeta1_hi": _round(z_hi, 4),
        "class_probs": probs, "class_map": cmap,
        "gem_taxonomy": f"{GEM.get(fam, 'CR/LFM')}/HEX:{st}",
        "stiffness": {"k_ratio": _round(k_ratio), "z": _round(zsc, 2), "flag": bool(k_ratio < 0.7)},
        "score": {"value": _round(score, 1), "lo": _round(max(score - half, 0), 1),
                  "hi": _round(min(score + half * 0.8, 100), 1), "prior_value": _round(prior, 1),
                  "prior_lo": _round(max(prior - prior_half, 0), 1),
                  "prior_hi": _round(min(prior + prior_half, 100), 1)},
        "damage": {"pga_0.15": dmg(0.15), "pga_0.30": dmg(0.30), "pga_0.60": dmg(0.60)},
        "drift": {"pct_per_year": _round(drift_pct, 2), "step_pct": _round(drift_pct * 0.8, 2) if alert else None,
                  "alert": bool(alert), "series": series},
        "spectrum": {"band": band, "f": [_round(x, 4) for x in fgrid],
                     "excess": [_round(x, 3) for x in exc]},
    })
    return rec


def make_records(footprints: dict, seed: int = 20261111, today: date | None = None) -> list[dict]:
    rng = np.random.default_rng(seed)
    today = today or date.today()
    out = []
    for f in footprints["features"]:
        lat, lon = geo.centroid(f["geometry"])
        out.append(make_record(f["properties"], lat, lon, rng, today))
    return out


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print("usage: python -m quakescore.service.fixtures <footprints.geojson> <out.json>")
        return 2
    recs = make_records(json.loads(Path(argv[0]).read_text("utf-8")))
    Path(argv[1]).write_text(json.dumps(recs), "utf-8")
    print(f"wrote {len(recs)} FIXTURE records to {argv[1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
