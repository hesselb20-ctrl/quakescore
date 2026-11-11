"""Regression tests for the simulator, the device pipeline and identification."""
import numpy as np
import pytest

from quakescore.device.pipeline import decimate_anchored, fir_taps, process_session
from quakescore.features import BANDS, band_freqs
from quakescore.ident.identify import identify
from quakescore.sim.building import Building, chain_modes, make_building
from quakescore.sim.excitation import ENVIRONMENTS, response_psd
from quakescore.sim.fast import FastSite, simulate_features
from quakescore.sim.phone import PHONE_MODELS, Placement, random_placement
from quakescore.sim.timedomain import simulate


def test_uniform_chain_matches_closed_form():
    n = 12
    f, phi, mm, gamma = chain_modes(np.ones(n), np.full(n, 400.0))
    j = np.arange(1, 4)
    exact = 2 * np.sqrt(400.0) * np.sin((2 * j - 1) * np.pi / (2 * (2 * n + 1))) / (2 * np.pi)
    assert np.allclose(f[:3], exact, rtol=1e-9)
    assert np.allclose(phi[-1], 1.0)


def test_building_tuning_and_damage():
    b = make_building(9)
    assert b.modes["x"].f[0] == pytest.approx(1 / (0.02 * 3.3 * 9), rel=1e-9)
    assert b.damaged(0.81).modes["x"].f[0] == pytest.approx(0.9 * b.modes["x"].f[0], rel=1e-9)


def test_fir_and_anchored_decimation():
    h = fir_taps(4)
    assert (len(h) - 1) % 8 == 0 and abs(h.sum() - 1) < 1e-6
    w = np.fft.rfft(h, 8192)
    f = np.fft.rfftfreq(8192)
    assert np.all(np.abs(np.abs(w[f <= 0.1]) - 1) < 2e-3)            # passband
    assert np.all(np.abs(w[f >= 0.125]) < 2e-4)                       # stopband, about 80 dB
    t = np.arange(40000) / 200.0
    x = np.sin(2 * np.pi * 3.0 * t)[:, None]
    for i0 in (0, 1, 7, 1234567):
        y, j0 = decimate_anchored(x, i0, 4)
        tt = (j0 * 4 - i0 + np.arange(len(y)) * 4) / 200.0
        assert np.allclose(y[:, 0], np.sin(2 * np.pi * 3.0 * tt), atol=2e-3)   # zero phase, anchored


def test_device_pipeline_matches_analytic_spectrum():
    rng = np.random.default_rng(1)
    b, env = make_building(9), ENVIRONMENTS["energetic"]
    p = Placement(PHONE_MODELS["low"], floor=9, yaw=0.6, tilt=(0.02, -0.015))
    raw = simulate(b, env, [p], 3600.0, 1.79e9, rng)[0]
    s = process_session(raw.ts, raw.acc, raw.meta)
    assert s.accept_fraction > 0.95
    for band in ("M", "H"):
        f = band_freqs(band)
        lo, hi = BANDS[band]["search"]
        sel = (f >= lo) & (f <= hi)
        G = response_psd(b, env, f, 9, p.pos)
        model = (G[:, 0, 0].real + G[:, 1, 1].real) * np.abs(p.mount_tf(f)) ** 2 + 2 * p.model.noise_psd(f)
        assert np.median(s.trace(band)[sel] / model[sel]) == pytest.approx(1.0, abs=0.03)


def _sessions(n, env, phone, count, rng, floor=None):
    b = make_building(n)
    site = FastSite(b, ENVIRONMENTS[env], floor or n)
    out = []
    for i in range(count):
        p = random_placement(rng, PHONE_MODELS[phone], floor or n, contributor=f"c{i % 4}")
        p.pos = (0.0, 0.0)
        out.append(simulate_features(b, ENVIRONMENTS[env], p, 6 * 3600.0, 86400.0 * i, rng, site=site))
    return b, out


def test_identify_recovers_first_modes_below_noise_floor():
    rng = np.random.default_rng(3)
    b, sess = _sessions(9, "energetic", "low", 12, rng)
    modes = identify(sess, n_boot=30, rng=rng)
    for d in "xy":
        ft, zt = b.modes[d].f[0], b.modes[d].zeta[0]
        m = min(modes, key=lambda m: abs(m.f / ft - 1))
        assert abs(m.f / ft - 1) < 0.005 and m.snr < 1.0             # peak is below the sensor noise
        assert abs(m.zeta / zt - 1) < 0.25
        assert m.f_ci[0] < ft < m.f_ci[1]


def test_noise_only_gives_no_modes():
    rng = np.random.default_rng(4)
    _, sess = _sessions(9, "typical", "mid", 10, rng, floor=0)
    assert identify(sess, z_min=7.0, n_boot=0) == []
