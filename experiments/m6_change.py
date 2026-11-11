"""Milestone 6: change detection with a synthetic damage test. All results are SIM (fast path).

A building is observed for a year. Its stiffness follows temperature (linear), an unobserved slow
environmental term (moisture and similar, AR(1)) and, half-way through, a permanent loss of 0, 2.5,
5, 10 or 20%. Sessions are grouped into epochs; each epoch gives one frequency estimate through the
registration against reference modes identified in the first quarter (quakescore/change/track.py).
The detector then looks for a lasting step.

Reported: detection probability by stiffness loss and number of sessions, at a threshold calibrated
on the zero-loss runs for a 5% false-alarm rate, and the minimum detectable loss at 90% detection.
"""
from __future__ import annotations

import numpy as np

from common import home_band, run_pool, save, seed_of
from quakescore.change.drift import detect_change
from quakescore.change.track import epoch_shift
from quakescore.ident.identify import identify
from quakescore.sim.building import make_building
from quakescore.sim.excitation import ENVIRONMENTS
from quakescore.sim.fast import FastSite, simulate_features
from quakescore.sim.phone import PHONE_MODELS, random_placement

LOSSES = (0.0, 0.025, 0.05, 0.10, 0.20)
EPOCH_SESSIONS = 5
TEMP_COEFF = -5e-4          # relative frequency change per degree C (ASSUMED; published wander is 0.3-3%)
SLOW_SIGMA = 0.003          # unobserved slow environmental wander of frequency, relative (ASSUMED)


def _trial(task):
    n, phone_name, loss, n_epochs, seed = task
    rng = np.random.default_rng(seed)
    b0 = make_building(n, rng, scatter=0.1)
    phone = PHONE_MODELS[phone_name]
    f1 = float(b0.modes["x"].f[0])
    band = home_band(f1)
    days = np.linspace(0, 364, n_epochs)
    temp = 12 + 8 * np.sin(2 * np.pi * (days - 110) / 365.25) + rng.normal(0, 2.5, n_epochs)
    slow = np.zeros(n_epochs)
    for i in range(1, n_epochs):
        slow[i] = 0.7 * slow[i - 1] + rng.normal(0, SLOW_SIGMA * np.sqrt(1 - 0.49))
    floor = max(1, int(round(0.8 * n)))
    n_ref = max(3, n_epochs // 4)                    # baseline period: the first quarter of the year
    epochs = []
    for e in range(n_epochs):
        rel_f = (1 + TEMP_COEFF * (temp[e] - 12)) * (1 + slow[e])
        k = rel_f**2 * (1 - loss if e >= n_epochs // 2 else 1.0)
        b = b0.damaged(k)
        env = ENVIRONMENTS[str(rng.choice(["typical", "energetic"], p=[0.5, 0.5]))]
        site = FastSite(b, env, floor, (0.0, 0.0), (band,))
        sess = []
        for s in range(EPOCH_SESSIONS):
            p = random_placement(rng, phone, floor, contributor=f"c{s % 3}")
            p.pos = (0.0, 0.0)
            sess.append(simulate_features(b, env, p, 6 * 3600.0, 86400.0 * days[e], rng, site=site, bands=(band,)))
        epochs.append(sess)
    # reference modes from the pooled baseline period, then one shift per epoch against them
    pooled = [s for sess in epochs[:n_ref] for s in sess]
    ref = [(m.f, m.zeta) for m in identify(pooled, z_min=6.0, n_boot=0, bands=(band,)) if 0.8 < m.f / f1 < 1.45 and m.zeta > 0.003]
    empty = {"n": n, "phone": phone_name, "loss": loss, "epochs": n_epochs, "usable": 0, "t": 0.0, "step": 0.0, "resid": None}
    if not ref:
        return empty
    f_ref = min(r[0] for r in ref)
    fest, keep = [], []
    for e, sess in enumerate(epochs):
        d, z = epoch_shift(sess, band, ref)
        if z >= 4.0:
            fest.append(f_ref * (1 + d))
            keep.append(e)
    if len(keep) < 7:
        return {**empty, "usable": len(keep)}
    keep = np.array(keep)
    r = detect_change(days[keep], np.array(fest), temp[keep], None, threshold=np.inf)
    return {"n": n, "phone": phone_name, "loss": loss, "epochs": n_epochs, "usable": int(len(keep)),
            "t": r.t_stat, "step": r.step, "resid": r.resid_sigma, "temp_coeff": r.temp_coeff}


def main() -> None:
    tasks = [(n, ph, loss, ne, seed_of("m6", n, ph, loss, ne, i))
             for n, ph in ((9, "low"), (25, "low"), (9, "mid"))
             for ne in (8, 12, 20, 40)
             for loss in LOSSES for i in range(30 if loss else 60)]
    rows = run_pool(_trial, tasks, label="m6", checkpoint="m6")
    summary = []
    for n, ph in ((9, "low"), (25, "low"), (9, "mid")):
        for ne in (8, 12, 20, 40):
            sub = [r for r in rows if r["n"] == n and r["phone"] == ph and r["epochs"] == ne]
            null = np.array([abs(r["t"]) for r in sub if r["loss"] == 0.0])
            thr = float(np.percentile(null, 95))
            rec = {"storeys": n, "phone": ph, "epochs": ne, "sessions_total": ne * EPOCH_SESSIONS,
                   "sessions_before_and_after": ne * EPOCH_SESSIONS // 2, "threshold_t": thr,
                   "usable_epoch_share": float(np.mean([r["usable"] / ne for r in sub])),
                   "resid_sigma_pct": float(100 * np.nanmedian([r["resid"] for r in sub if r["resid"] is not None] or [np.nan])),
                   "detect": {}, "step_est_pct": {}}
            for loss in LOSSES[1:]:
                g = [r for r in sub if r["loss"] == loss]
                rec["detect"][str(loss)] = float(np.mean([(abs(r["t"]) > thr) and (r["step"] < 0) for r in g]))
                rec["step_est_pct"][str(loss)] = float(100 * np.median([r["step"] for r in g]))
            ok = [loss for loss in LOSSES[1:] if rec["detect"][str(loss)] >= 0.9]
            rec["min_detectable_loss"] = min(ok) if ok else None
            summary.append(rec)
            print(rec)
    save("m6/change_detection.json", {"assumptions": {"temp_coeff_per_C": TEMP_COEFF, "slow_sigma": SLOW_SIGMA,
                                                      "epoch_sessions": EPOCH_SESSIONS, "false_alarm_rate": 0.05},
                                      "summary": summary, "rows": rows})


if __name__ == "__main__":
    main()
