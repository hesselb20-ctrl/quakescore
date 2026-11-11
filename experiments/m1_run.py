"""Milestone 1 experiments: simulator and identification core. All results are SIM.

Usage: python experiments/m1_run.py [e1 e2 e3 e4a e4b e5]
  e1  fast spectral path against the time-domain path
  e2  estimator comparison on time-domain sessions (curve fit, FDD peak, EFDD, SSI-COV, random decrement)
  e3  detection limit: height x environment x phone noise x floor x number of sessions
  e4a error against record length
  e4b several simultaneous phones: incoherent stacking against coherent FDD, sync error, mode shape
  e5  false alarms on structure-free noise
"""
from __future__ import annotations

import dataclasses
import sys

import numpy as np
from scipy import signal

from common import bands_for, first_mode, home_band, mode_signal, n_spurious, run_pool, save, seed_of
from quakescore.device.pipeline import process_session
from quakescore.features import BANDS, band_freqs
from quakescore.ident.estimators import fdd, mode_shape, random_decrement
from quakescore.ident.identify import identify
from quakescore.ident.stack import build_stack, matched_filter
from quakescore.sim.building import make_building
from quakescore.sim.excitation import ENVIRONMENTS
from quakescore.sim.fast import FastSite, simulate_features, simulate_sync_frames, windows_in
from quakescore.sim.phone import PHONE_MODELS, Placement, random_placement
from quakescore.sim.timedomain import simulate

PHONES = dict(PHONE_MODELS)
# noise floor implied by published MyShake phone spectra for recent models; not reconciled with
# datasheet densities (docs/references.md), so it is a sensitivity case only
PHONES["best"] = dataclasses.replace(PHONE_MODELS["low"], name="best", noise_ug=25.0, corner_hz=0.3)
PREFIX = (1, 2, 5, 10, 20, 50)
NIGHT = 6 * 3600.0


def _floor(n: int, frac: float) -> int:
    return max(1, int(round(frac * n)))


# ----------------------------------------------------------------------------------------- e1
def _e1(task):
    n, env_name, phone_name, seed = task
    rng = np.random.default_rng(seed)
    b, env, phone = make_building(n), ENVIRONMENTS[env_name], PHONES[phone_name]
    td, fa = [], []
    site = FastSite(b, env, n)
    for i in range(4):
        p = Placement(phone, floor=n, yaw=float(rng.uniform(0, 6.28)), mount_f=45.0, contributor=f"c{i}")
        raw = simulate(b, env, [p], 4 * 3600.0, 1.79e9 + 86400 * i, rng)[0]
        td.append(process_session(raw.ts, raw.acc, raw.meta))
        fa.append(simulate_features(b, env, p, 4 * 3600.0, 0.0, rng, site=site))
    out = {"n": n, "env": env_name, "phone": phone_name, "bands": {}}
    for band in "LMH":
        f = band_freqs(band)
        lo, hi = BANDS[band]["search"]
        sel = (f >= lo) & (f <= hi)
        p0 = Placement(phone, floor=n, mount_f=45.0)
        exp = site.expected(band, p0)
        exp_t = (exp[:, 0, 0].real + exp[:, 1, 1].real) / np.sinc(f / phone.fs_nominal) ** 4
        st_td, st_fa = build_stack(td, band), build_stack(fa, band)
        k = st_td.k.sum()
        r_td, r_fa = st_td.mean()[sel] / exp_t[sel], st_fa.mean()[sel] / exp_t[sel]
        out["bands"][band] = {
            "windows": float(k), "expected_scatter": float(1 / np.sqrt(2 * k)),
            "td_ratio_median": float(np.median(r_td)), "td_ratio_scatter": float(np.std(np.log(r_td))),
            "fast_ratio_median": float(np.median(r_fa)), "fast_ratio_scatter": float(np.std(np.log(r_fa)))}
    for name, sess in (("td", td), ("fast", fa)):
        modes = identify(sess, n_boot=0)
        out[name] = {d: first_mode(modes, b, d) for d in "xy"}
    return out


def e1():
    tasks = [(5, "energetic", "low", 11), (9, "energetic", "low", 12), (25, "energetic", "low", 13),
             (9, "energetic", "mid", 14), (40, "energetic", "mid", 15), (3, "energetic", "low", 16)]
    save("m1/e1_fast_vs_timedomain.json", run_pool(_e1, tasks, label="e1"))


# ----------------------------------------------------------------------------------------- e2
def _rdt_session(raw, f0: float) -> float:
    """Random decrement damping from raw device data along the principal horizontal axis."""
    fs = (len(raw.ts) - 1) / (raw.ts[-1] - raw.ts[0])
    q = max(1, int(fs / max(8 * f0, 25.0)))
    xy = raw.acc[:, :2] - raw.acc[:, :2].mean(0)
    if q > 1:
        xy = signal.decimate(xy, q, ftype="fir", axis=0)
    fsd = fs / q
    sos = signal.butter(4, [f0 * 0.85, f0 * 1.15], btype="band", fs=fsd, output="sos")
    bp = signal.sosfiltfilt(sos, xy, axis=0)
    w, v = np.linalg.eigh(np.cov(bp.T))
    est = random_decrement(xy @ v[:, -1], fsd, f0)
    return est.zeta if est.ok else float("nan")


def _e2(task):
    n, env_name, phone_name, seed = task
    rng = np.random.default_rng(seed)
    b, env, phone = make_building(n, rng, scatter=0.1), ENVIRONMENTS[env_name], PHONES[phone_name]
    sess, raws = [], []
    for i in range(6):
        p = random_placement(rng, phone, n, soft_mount_prob=0.0, contributor=f"c{i % 3}")
        p.pos = (0.0, 0.0)
        raw = simulate(b, env, [p], 4 * 3600.0, 1.79e9 + 86400 * i, rng)[0]
        sess.append(process_session(raw.ts, raw.acc, raw.meta))
        raws.append(raw)
    modes = identify(sess, n_boot=60, rng=rng, compare=True, bands=bands_for([b.modes["x"].f[0], b.modes["y"].f[0]]))
    out = {"n": n, "env": env_name, "phone": phone_name, "modes": {}}
    for d in "xy":
        ft, zt = float(b.modes[d].f[0]), float(b.modes[d].zeta[0])
        best = min(modes, key=lambda m: abs(m.f / ft - 1), default=None)
        rec = {"snr": None, "fit": None}
        if best is not None and abs(best.f / ft - 1) < 0.05:
            rdt = [_rdt_session(r, best.f) for r in raws]
            rec = {"snr": best.snr, "z": best.z,
                   "fit": [best.f / ft - 1, best.zeta / zt - 1],
                   "fit_ci_cover_f": bool(best.f_ci[0] <= ft <= best.f_ci[1]),
                   "fit_ci_cover_zeta": bool(best.zeta_ci[0] <= zt <= best.zeta_ci[1]),
                   "fit_ci_zeta_width": (best.zeta_ci[1] - best.zeta_ci[0]) / zt,
                   "fdd_peak": [best.alt["fdd_peak"]["f"] / ft - 1, None],
                   "efdd": [best.alt["efdd"]["f"] / ft - 1, best.alt["efdd"]["zeta"] / zt - 1],
                   "ssi": [best.alt["ssi"]["f"] / ft - 1, best.alt["ssi"]["zeta"] / zt - 1],
                   "rdt": [None, float(np.nanmedian(rdt)) / zt - 1 if np.isfinite(rdt).any() else None]}
        out["modes"][d] = rec
    return out


def e2():
    tasks = [(n, env, ph, 1000 + 97 * i + 13 * n + (0 if env == "typical" else 5))
             for n in (3, 9, 25, 40) for env, ph in (("energetic", "low"), ("energetic", "mid"), ("typical", "low"))
             for i in range(6)]
    save("m1/e2_methods.json", run_pool(_e2, tasks, label="e2"))


# ----------------------------------------------------------------------------------------- e3
def _e3(task):
    n, env_name, phone_name, frac, seed = task
    rng = np.random.default_rng(seed)
    b, env, phone = make_building(n, rng, scatter=0.15), ENVIRONMENTS[env_name], PHONES[phone_name]
    floor = _floor(n, frac)
    bands = bands_for([b.modes["x"].f[0], b.modes["y"].f[0]])
    site = FastSite(b, env, floor, (0.0, 0.0), bands)
    sess = []
    for i in range(max(PREFIX)):
        p = random_placement(rng, phone, floor, contributor=f"c{i % 5}")
        p.pos = (0.0, 0.0)
        sess.append(simulate_features(b, env, p, NIGHT, 86400.0 * i, rng, site=site, bands=bands))
    rec = {"n": n, "env": env_name, "phone": phone_name, "frac": frac, "floor": floor,
           "signal": mode_signal(b, env, phone, floor), "by_n": {}}
    for ns in PREFIX:
        modes = identify(sess[:ns], n_boot=0, bands=bands)
        rec["by_n"][ns] = {"x": first_mode(modes, b, "x"), "y": first_mode(modes, b, "y"),
                           "spurious": n_spurious(modes, b)}
    return rec


def e3():
    tasks = []
    for n in (2, 3, 5, 7, 9, 12, 15, 25, 40):
        for env in ("quiet", "typical", "energetic"):
            for ph in ("low", "mid", "high"):
                for frac in (1.0, 0.5):
                    tasks += [(n, env, ph, frac, seed_of(n, env, ph, frac, i)) for i in range(12)]
    for n in (3, 9, 25):
        for env in ("quiet", "typical", "energetic"):
            tasks += [(n, env, "best", 1.0, seed_of(n, env, "best", i)) for i in range(12)]
    save("m1/e3_detection_limit.json", run_pool(_e3, tasks, label="e3", checkpoint="m1_e3"))


# ----------------------------------------------------------------------------------------- e4a
def _e4a(task):
    n, env_name, phone_name, hours, ns, seed = task
    rng = np.random.default_rng(seed)
    b, env, phone = make_building(n, rng, scatter=0.1), ENVIRONMENTS[env_name], PHONES[phone_name]
    bands = bands_for([b.modes["x"].f[0], b.modes["y"].f[0]])
    site = FastSite(b, env, n, (0.0, 0.0), bands)
    sess = []
    for i in range(ns):
        p = random_placement(rng, phone, n, contributor=f"c{i % 5}")
        p.pos = (0.0, 0.0)
        sess.append(simulate_features(b, env, p, hours * 3600.0, 86400.0 * i, rng, site=site, bands=bands))
    modes = identify(sess, n_boot=0, bands=bands)
    return {"n": n, "env": env_name, "phone": phone_name, "hours": hours, "sessions": ns,
            "x": first_mode(modes, b, "x"), "y": first_mode(modes, b, "y")}


def e4a():
    tasks = [(n, env, "low", h, ns, seed_of(n, env, h, ns, i))
             for n in (9, 25) for env in ("typical", "energetic") for h in (0.5, 1.0, 2.0, 4.0, 8.0)
             for ns in (5, 20) for i in range(16)]
    save("m1/e4a_record_length.json", run_pool(_e4a, tasks, label="e4a"))


# ----------------------------------------------------------------------------------------- e4b
def _z_at(f, spec, band, f0):
    centres, z, _ = matched_filter(f, spec, band)
    near = np.abs(f[centres] / f0 - 1) < 0.02
    return float(z[near].max()) if near.any() else float("nan")


def _e4b(task):
    n, env_name, phone_name, n_phones, sync, seed = task
    rng = np.random.default_rng(seed)
    b, env, phone = make_building(n, rng, scatter=0.1), ENVIRONMENTS[env_name], PHONES[phone_name]
    f1 = float(b.modes["x"].f[0])
    band = home_band(f1)
    floors = np.unique(np.round(np.linspace(0.3 * n, n, n_phones)).astype(int)) if n_phones > 1 else np.array([n])
    while len(floors) < n_phones:
        floors = np.sort(np.append(floors, rng.integers(max(1, n // 3), n + 1)))
    ps = []
    for fl in floors[:n_phones]:
        p = random_placement(rng, phone, int(fl), soft_mount_prob=0.0, sync_sigma=sync)
        p.pos = (0.0, 0.0)
        ps.append(p)
    k = windows_in(NIGHT, band)
    f, X = simulate_sync_frames(b, env, ps, band, (0.0, 1e9), k, rng)
    psd = (np.abs(X[:, :, :, :2]) ** 2).mean(0)                      # (f, phone, axis)
    level = np.median(psd.sum(2), 0)
    incoh = (psd.sum(2) / level[None] ** 2).sum(1) / (1 / level**2).sum()
    s, _, G = fdd(X)
    rec = {"n": n, "env": env_name, "phone": phone_name, "phones": n_phones, "sync_ms": 1e3 * sync,
           "z_incoherent": _z_at(f, incoh, band, f1), "z_coherent": _z_at(f, s[:, 0], band, f1)}
    if n_phones >= 3:
        est = mode_shape(G, f, f1, float(b.modes["x"].zeta[0]))
        true = np.array([b.modes["x"].phi[p.floor - 1, 0] for p in ps])
        true = true / true.max()
        rec["shape_rms_err"] = float(np.sqrt(np.mean((est - true) ** 2)))
    return rec


def e4b():
    tasks = [(n, env, "low", npn, sync, seed_of(n, env, npn, sync, i))
             for n, env in ((9, "energetic"), (25, "energetic"), (25, "typical"), (9, "typical"))
             for npn in (1, 2, 4, 8) for sync in (0.005, 0.05, 0.2) for i in range(10)]
    save("m1/e4b_phones.json", run_pool(_e4b, tasks, workers=4, label="e4b"))


# ----------------------------------------------------------------------------------------- e5
def _e5(seed):
    rng = np.random.default_rng(seed)
    b, env = make_building(int(rng.integers(2, 30))), ENVIRONMENTS[str(rng.choice(["quiet", "typical", "energetic"]))]
    site = FastSite(b, env, 0)                                        # ground floor: no structural response
    sess = []
    for i in range(20):
        ph = PHONES[str(rng.choice(["low", "mid", "high"]))]
        p = Placement(ph, floor=0, yaw=float(rng.uniform(0, 6.28)), mount_f=200.0, contributor=f"c{i % 5}")
        sess.append(simulate_features(b, env, p, NIGHT, 86400.0 * i, rng, site=site))
    zs = sorted((m.z for m in identify(sess, z_min=4.5, n_boot=0)), reverse=True)
    return zs


def e5():
    zs = run_pool(_e5, list(range(5000, 5400)), label="e5")
    out = {"stacks": len(zs), "sessions_per_stack": 20}
    for thr in (5.0, 5.5, 6.0, 7.0):
        out[f"stacks_with_false_peak_z{thr}"] = int(sum(1 for z in zs if z and z[0] >= thr))
        out[f"false_peaks_z{thr}"] = int(sum(sum(1 for v in z if v >= thr) for z in zs))
    save("m1/e5_false_alarms.json", out)


if __name__ == "__main__":
    which = sys.argv[1:] or ["e1", "e2", "e3", "e4a", "e4b", "e5"]
    for name in which:
        globals()[name]()
