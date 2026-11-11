"""Milestone 4: artefact rejection on a labelled set of contaminated sessions. All results are SIM.

Time-domain simulation, so tones, aliases, bursts, footsteps and the stationarity gate are all
exercised. Each building has persistent machinery (same frequencies every night), per-night
appliances and footsteps, a mix of furniture couplings, calm and windy nights, and three phone
models, one of which has a self-noise resonance and a 1 Hz housekeeping tick in every building.

Labels. Every candidate peak is compared with the building's true modes and with every interference
frequency injected into its sessions:
    structural      within 2% of a true mode and not on an interference line
    non-structural  on an interference line, or more than 4% from every true mode
    ambiguous       near both, or 2-4% from a true mode (blended or shifted); excluded from the rates

Two results are reported: all candidates, and the modes the product would publish (the lowest three
accepted modes inside the plausibility window for the building's height).
"""
from __future__ import annotations

import pickle
import sys

import numpy as np

from common import RESULTS, run_pool, save, seed_of
from quakescore.artefacts.reject import RejectConfig, apply, model_peaks, pick_fundamental, registry_from_peaks
from quakescore.device.pipeline import process_session
from quakescore.features import BANDS, NFFT
from quakescore.ident.identify import identify
from quakescore.sim.building import make_building
from quakescore.sim.excitation import ENVIRONMENTS
from quakescore.sim.interference import BuildingNoise
from quakescore.sim.phone import PHONE_MODELS, random_placement
from quakescore.sim.timedomain import simulate

N_BUILDINGS = 48
N_SESSIONS = 9
HOURS = 4.0


SET = "test" if "--test" in sys.argv else "tune"     # thresholds were set on "tune"; "test" is held out


def _simulate_building(task):
    i, tag = task
    rng = np.random.default_rng(seed_of("m4", i) if tag == "tune" else seed_of("m4-test", i))
    n = int(rng.choice([3, 4, 5, 7, 9, 12, 15, 20, 25, 30]))
    b = make_building(n, rng, scatter=0.15)
    b.building_id = f"m4-{i}"
    noise = BuildingNoise.draw(rng)
    sessions, lines = [], []
    for s in range(N_SESSIONS):
        model = PHONE_MODELS[("low", "mid", "mid_res")[s % 3]]
        floor = int(rng.integers(max(1, n // 2), n + 1))
        p = random_placement(rng, model, floor, b.width, soft_mount_prob=0.25, contributor=f"c{s % 4}")
        itf = noise.session(rng, HOURS * 3600.0)
        env = ENVIRONMENTS[str(rng.choice(["typical", "energetic"]))]      # windy and calm nights mixed
        raw = simulate(b, env, [p], HOURS * 3600.0, 1.79e9 + 86400.0 * s, rng, interference=itf)[0]
        feat = process_session(raw.ts, raw.acc, raw.meta)
        feat.session_id = f"m4-{i}-{s}"
        sessions.append(feat)
        lines += itf.lines()
    return {"id": b.building_id, "n": n, "truth": b.true_modes(), "sessions": sessions, "lines": lines,
            "hvac": noise.hvac, "elevator_hz": noise.elevator_hz,
            "accept": float(np.mean([s.accept_fraction for s in sessions]))}


def _identify(rec):
    modes = identify(rec["sessions"], z_min=6.0, n_boot=40, rng=np.random.default_rng(seed_of(rec["id"])))
    return rec["id"], modes, model_peaks(rec["sessions"])


def _df(f: float) -> float:
    band = "L" if f < 1.0 else ("M" if f < 4.0 else "H")
    return BANDS[band]["fs"] / NFFT


def _folded(rec) -> list[tuple[float, str]]:
    """Injected line frequencies, with those above Nyquist folded at each session's true sample rate."""
    out = []
    for fl, kind in rec["lines"]:
        if fl <= 25.0:
            out.append((fl, kind))
            continue
        for s in rec["sessions"]:
            fs = s.fs_raw
            out.append((abs(fl - round(fl / fs) * fs), "mains"))
    return out


def _interference_at(f: float, lines) -> str | None:
    """Name of the injected interference that explains a peak at f, if any."""
    tol = max(0.006 * f, 3 * _df(f))
    if abs(f / 2.9 - 1) < 0.02:
        return "phone resonance"
    if 0.9 < f < 24.5 and abs(f - round(f)) < tol:
        return "phone tick harmonic"
    for fl, kind in lines:
        if kind == "elevator":
            if abs(f / fl - 1) < 0.10:
                return "elevator"
        elif abs(f - fl) < tol:
            return {"hvac": "hvac tone", "mains": "mains alias", "appliance": "appliance"}.get(kind, kind)
    return None


def _label(f: float, rec, lines) -> tuple[str, str]:
    d = min(abs(f / t["f"] - 1) for t in rec["truth"])
    src = _interference_at(f, lines)
    if d < 0.02 and src is None:
        return "structural", "true mode"
    if src is not None and d >= 0.02:
        return "non-structural", src
    if src is None and d >= 0.04:
        return "non-structural", "other (furniture, blend, noise)"
    return "ambiguous", src or "near a true mode"


def main() -> None:
    cache = RESULTS / "cache" / ("m4_buildings.pkl" if SET == "tune" else "m4_buildings_test.pkl")
    if cache.exists() and "--resim" not in sys.argv:
        recs = pickle.loads(cache.read_bytes())
    else:
        recs = run_pool(_simulate_building, [(i, SET) for i in range(N_BUILDINGS)], label="m4 simulate")
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(pickle.dumps(recs))
    by_id = {r["id"]: r for r in recs}
    out3 = run_pool(_identify, recs, label="m4 identify")
    found = {bid: modes for bid, modes, _ in out3}
    registry = registry_from_peaks([mp for _, _, mp in out3])
    cfg = RejectConfig()
    rows, breakdown, reasons = [], {}, {}
    pub = {"structural": 0, "non-structural": 0, "ambiguous": 0}
    fund = {"buildings": len(recs), "first_mode_detected": 0, "reported": 0, "reported_correct": 0, "reported_wrong": 0}
    for bid, modes in found.items():
        rec = by_id[bid]
        lines = _folded(rec)
        apply(modes, cfg, registry)
        first = [t["f"] for t in rec["truth"] if t["order"] == 1 and t["dir"] in "xy"]
        for m in modes:
            lab, src = _label(m.f, rec, lines)
            rows.append({"building": bid, "f": m.f, "zeta": m.zeta, "z": m.z, "truth": lab, "source": src, "label": m.label,
                         "tone": m.features["tone"], "top1_share": m.features["top1_share"],
                         "vertical_ratio": m.features["vertical_ratio"], "vertical_z": m.features["vertical_z"]})
            if lab == "non-structural":
                d = breakdown.setdefault(src, {"candidates": 0, "passed": 0})
                d["candidates"] += 1
                d["passed"] += m.label == "structural"
            key = f"{lab}: {m.label}"
            reasons[key] = reasons.get(key, 0) + 1
        f_exp = min(first)                    # stands in for the height-based expectation
        ok = sorted((m for m in modes if m.label == "structural" and cfg.plaus_lo * f_exp <= m.f <= cfg.plaus_hi * f_exp),
                    key=lambda m: m.f)[:3]
        for m in ok:
            pub[_label(m.f, rec, lines)[0]] += 1
        fund["first_mode_detected"] += any(abs(m.f / f_exp - 1) < 0.02 for m in modes)
        pick = pick_fundamental(modes, f_exp, cfg)
        if pick is not None:
            fund["reported"] += 1
            good = min(abs(pick.f / ft - 1) for ft in first) < 0.02
            fund["reported_correct"] += good
            fund["reported_wrong"] += not good
    cand = {k: sum(r["truth"] == k for r in rows) for k in ("structural", "non-structural", "ambiguous")}
    kept = {k: sum(r["truth"] == k and r["label"] == "structural" for r in rows) for k in cand}
    res = {
        "set": SET, "buildings": len(recs), "sessions": len(recs) * N_SESSIONS, "hours_per_session": HOURS,
        "mean_window_accept_fraction": float(np.mean([r["accept"] for r in recs])),
        "candidates": cand, "accepted": kept,
        "false_share_before": cand["non-structural"] / max(cand["structural"] + cand["non-structural"], 1),
        "false_share_after": kept["non-structural"] / max(kept["structural"] + kept["non-structural"], 1),
        "structural_retention": kept["structural"] / max(cand["structural"], 1),
        "published": pub, "published_false_share": pub["non-structural"] / max(pub["structural"] + pub["non-structural"], 1),
        "fundamental": fund, "false_by_source": breakdown, "label_counts": reasons,
        "registry": {k: [round(v, 3) for v in vals] for k, vals in registry.items()},
        "config": cfg.__dict__, "rows": rows,
    }
    save("m4/artefact_rejection.json" if SET == "tune" else "m4/artefact_rejection_test.json", res)
    print({k: v for k, v in res.items() if k not in ("rows", "config", "label_counts")})


if __name__ == "__main__":
    main()
