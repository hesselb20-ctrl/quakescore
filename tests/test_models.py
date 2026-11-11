"""Regression tests for artefact rejection, the vulnerability model and change detection."""
import numpy as np
import pytest

from quakescore.artefacts.reject import apply, pick_fundamental
from quakescore.change.drift import detect_change
from quakescore.ident.identify import identify
from quakescore.sim.building import make_building
from quakescore.sim.excitation import ENVIRONMENTS
from quakescore.sim.fast import FastSite, simulate_features
from quakescore.sim.phone import PHONE_MODELS, random_placement
from quakescore.vuln.fragility import capacity, mean_damage_ratio, tables
from quakescore.vuln.score import Attributes, Measurement, mode_order_probability, quakescore


def test_structural_modes_pass_rejection_and_fundamental_is_picked():
    rng = np.random.default_rng(3)
    b = make_building(9)
    site = FastSite(b, ENVIRONMENTS["energetic"], 9)
    sess = []
    for i in range(12):
        p = random_placement(rng, PHONE_MODELS["low"], 9, contributor=f"c{i % 4}")
        p.pos = (0.0, 0.0)
        sess.append(simulate_features(b, ENVIRONMENTS["energetic"], p, 6 * 3600.0, 86400.0 * i, rng, site=site))
    modes = apply(identify(sess, n_boot=30, rng=rng))
    first = [m for m in modes if abs(m.f / b.modes["x"].f[0] - 1) < 0.01]
    assert first and first[0].label == "structural"
    assert pick_fundamental(modes).f == pytest.approx(b.modes["x"].f[0], rel=0.005)


def test_capacity_curve_and_class_ordering():
    lv = tables()["W1"]["levels"]["high"]
    sd = np.array([lv["Dy"], lv["Du"], 2 * lv["Du"]])
    assert np.allclose(capacity(sd, lv["Dy"], lv["Ay"], lv["Du"], lv["Au"]), [lv["Ay"], lv["Au"], lv["Au"]], rtol=1e-3)
    h = tables()["C1M"]["roof_ht_ft"] * 0.3048
    mdr = [mean_damage_ratio("C1M", level, h)[0] for level in ("high", "moderate", "low", "pre")]
    assert mdr == sorted(mdr)                                          # better code, less damage
    assert mean_damage_ratio("C1M", "moderate", h, t_ratio=1.4)[0] > mdr[1]     # softer is worse
    assert mean_damage_ratio("C1M", "moderate", h, dcf_ratio=2.0)[0] > mdr[1]   # drift concentration is worse


def test_score_band_narrows_with_measurement_and_mode_order():
    a = Attributes(height_m=30.0, storeys=9, year=1968)
    prior = quakescore(a, None, 200, np.random.default_rng(0))
    meas = quakescore(a, Measurement(1.7, (1.69, 1.71), 0.02, (0.018, 0.023)), 200, np.random.default_rng(0))
    assert 0 <= prior.lo <= prior.score <= prior.hi <= 100
    assert (meas.hi - meas.lo) < (prior.hi - prior.lo)
    assert mode_order_probability(a, 1.3) > 0.9 and mode_order_probability(a, 4.2) < 0.5


def test_detect_change_finds_step_and_ignores_temperature():
    rng = np.random.default_rng(7)
    t = np.arange(30) * 12.0
    temp = 12 + 8 * np.sin(2 * np.pi * t / 365.25) + rng.normal(0, 1, 30)
    base = 1.7 * (1 - 5e-4 * (temp - 12)) * (1 + rng.normal(0, 0.002, 30))
    assert not detect_change(t, base, temp).alarm
    stepped = base * np.where(t >= 180, 0.95, 1.0)
    r = detect_change(t, stepped, temp)
    assert r.alarm and r.step == pytest.approx(-0.05, abs=0.01) and abs(r.onset - 180) <= 24
