"""Batch job: turn one building's uploaded sessions into the record the API serves.

Pipeline: identify -> reject artefacts -> pick the fundamental -> class, stiffness anomaly and
QuakeScore -> change detection on the frequency history -> record. The record schema is documented in
docs/api.md. Measured outputs are released only above the K-threshold; below it the record carries
coverage and the class-based prior only.
"""
from __future__ import annotations

import datetime as dt

import numpy as np

from .artefacts.reject import RejectConfig, apply, pick_fundamental
from .change.drift import detect_change
from .features import SessionFeatures
from .ident.identify import identify
from .ident.stack import baseline, build_stack
from .vuln.score import Attributes, Measurement, class_prior, expected_period, mode_order_probability, quakescore

K_CONTRIBUTORS = 3
K_SESSIONS = 5
MODE_ORDER_MIN = 0.8


def _round(v, n=4):
    return None if v is None or not np.isfinite(v) else round(float(v), n)


def _spectrum(sessions: list[SessionFeatures], band: str, f1: float, max_points: int = 240) -> dict | None:
    st = build_stack(sessions, band)
    if st is None:
        return None
    t = st.mean()
    ex = t / baseline(st.f, t) - 1.0
    sel = np.flatnonzero((st.f >= 0.35 * f1) & (st.f <= min(4.0 * f1, 0.8 * st.f[-1])))
    if len(sel) < 8:
        return None
    step = max(1, len(sel) // max_points)
    idx = sel[: len(sel) // step * step].reshape(-1, step)
    best = idx[np.arange(len(idx)), np.abs(ex[idx]).argmax(1)]
    return {"band": band, "f": [round(float(v), 4) for v in st.f[best]], "excess": [round(float(v), 4) for v in ex[best]]}


def building_record(building_id: str, attrs: dict, sessions: list[SessionFeatures],
                    registry: dict | None = None, history: list | None = None,
                    rng: np.random.Generator | None = None, provenance: str = "SIM",
                    region: str = "us_west", updated: str | None = None, n_boot: int = 60) -> dict:
    """attrs: storeys, height_m, year, material, use, lat, lon, name, address (any may be None)."""
    rng = rng or np.random.default_rng(0)
    storeys = int(attrs.get("storeys") or max(1, round((attrs.get("height_m") or 6.0) / 3.3)))
    height = float(attrs.get("height_m") or 3.3 * storeys)
    a = Attributes(height_m=height, storeys=storeys, year=attrs.get("year"), material=attrs.get("material"), region=region)
    prior = quakescore(a, None, 200, rng)
    n_contrib = len({s.contributor for s in sessions})
    rec = {
        "building_id": building_id, "provenance": provenance,
        "updated": updated or dt.date.today().isoformat(),
        "attrs": {**{k: attrs.get(k) for k in ("year", "material", "use", "lat", "lon", "name", "address")},
                  "storeys": storeys, "height_m": round(height, 1)},
        "coverage": {"sessions": len(sessions), "contributors": n_contrib,
                     "floors": len({s.floor for s in sessions}), "status": "no_data", "sessions_needed": None},
        "modes": [], "f1": None, "f1_lo": None, "f1_hi": None, "zeta1": None, "zeta1_lo": None, "zeta1_hi": None,
        "class_probs": prior.class_probs, "class_map": prior.class_map, "gem_taxonomy": prior.gem_taxonomy,
        "stiffness": None, "score": None, "damage": None, "drift": None, "spectrum": None,
        "prior": {"value": _round(prior.score, 1), "lo": _round(prior.lo, 1), "hi": _round(prior.hi, 1)},
    }
    if not sessions:
        return rec
    rec["coverage"]["status"] = "needs_data"
    released = n_contrib >= K_CONTRIBUTORS and len(sessions) >= K_SESSIONS
    cfg = RejectConfig()
    modes = apply(identify(sessions, n_boot=n_boot, rng=rng), cfg, registry)
    cp = class_prior(a)
    f_exp = 1.0 / sum(p * expected_period(c, height) for c, p in cp.items())
    fund = pick_fundamental(modes, f_exp, cfg)
    if fund is None:
        cand = [m for m in modes if not m.label.startswith("rejected:too") and cfg.plaus_lo * f_exp <= m.f <= cfg.plaus_hi * f_exp]
        if cand:
            z = max(m.z for m in cand)
            rec["coverage"]["sessions_needed"] = int(max(1, np.ceil(len(sessions) * ((cfg.z_release / z) ** 2 - 1))))
        if n_contrib < K_CONTRIBUTORS or len(sessions) < K_SESSIONS:
            need_k = max(K_SESSIONS - len(sessions), K_CONTRIBUTORS - n_contrib, 0)
            rec["coverage"]["sessions_needed"] = max(rec["coverage"]["sessions_needed"] or 0, need_k)
        return rec
    if not released:
        rec["coverage"]["sessions_needed"] = max(K_SESSIONS - len(sessions), K_CONTRIBUTORS - n_contrib, 1)
        return rec
    p_first = mode_order_probability(a, fund.f)
    if p_first < MODE_ORDER_MIN:
        # the lowest identified peak may be a second mode; do not score on a guess
        rec["coverage"]["reason"] = "mode order ambiguous"
        return rec
    rec["coverage"]["status"] = "scored"
    rec["coverage"]["sessions_needed"] = 0
    rec["modes"] = [{"f": _round(m.f), "f_lo": _round(m.f_ci[0]), "f_hi": _round(m.f_ci[1]), "zeta": _round(m.zeta),
                     "zeta_lo": _round(m.zeta_ci[0]), "zeta_hi": _round(m.zeta_ci[1]), "z": _round(m.z, 1),
                     "label": m.label} for m in modes]
    rec.update(f1=_round(fund.f), f1_lo=_round(fund.f_ci[0]), f1_hi=_round(fund.f_ci[1]), zeta1=_round(fund.zeta),
               zeta1_lo=_round(fund.zeta_ci[0]), zeta1_hi=_round(fund.zeta_ci[1]))
    ci_ok = bool(np.all(np.isfinite(fund.f_ci)))
    meas = Measurement(fund.f, fund.f_ci if ci_ok else (fund.f * 0.98, fund.f * 1.02), fund.zeta,
                       fund.zeta_ci if np.all(np.isfinite(fund.zeta_ci)) else None)
    res = quakescore(a, meas, 300, rng)
    rec.update(class_probs=res.class_probs, class_map=res.class_map, gem_taxonomy=res.gem_taxonomy, damage=res.damage)
    rec["stiffness"] = {"k_ratio": _round(res.k_ratio, 3), "z": _round(res.anomaly_z, 2), "flag": res.anomaly_flag}
    rec["score"] = {"value": _round(res.score, 1), "lo": _round(res.lo, 1), "hi": _round(res.hi, 1),
                    "prior_value": _round(prior.score, 1), "prior_lo": _round(prior.lo, 1), "prior_hi": _round(prior.hi, 1)}
    rec["spectrum"] = _spectrum(sessions, fund.band, fund.f)
    if history and len(history) >= 7:
        days = np.array([h[0] for h in history], float)
        ch = detect_change(days, np.array([h[1] for h in history]), np.array([h[3] for h in history]) if len(history[0]) > 3 else None)
        base_day = dt.date.fromisoformat(rec["updated"]) - dt.timedelta(days=float(days.max()))
        rec["drift"] = {"pct_per_year": _round(100 * ch.trend_per_year, 2),
                        "step_pct": _round(100 * ch.step, 2) if ch.alarm else None, "alert": bool(ch.alarm and ch.step < 0),
                        "series": [[(base_day + dt.timedelta(days=float(h[0]))).isoformat(), _round(h[1]), _round(h[2])] for h in history]}
    return rec
