"""Full time-domain session simulator: building response sampled by imperfect phones.

Produces raw (timestamp, acceleration) streams exactly as an app would see them, including
quantisation, non-nominal sample rate, timestamp jitter, clock error, tilt, yaw, furniture coupling
and interference. Phones passed together share the same building motion, so their recordings are
mutually coherent.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import fft as sfft

from .building import G0, Building
from .excitation import Environment
from .interference import InterferenceSet
from .phone import Placement

FS_SIM = 200.0
F_STRUCT_MAX = 25.0


@dataclass
class RawSession:
    ts: np.ndarray            # reported UTC timestamps, s
    acc: np.ndarray           # (n, 3) device-frame specific force, m/s^2
    meta: dict


def _coloured(rng: np.random.Generator, n: int, fs: float, psd_fn) -> np.ndarray:
    """Gaussian noise of length n with the given one-sided PSD."""
    nf = sfft.next_fast_len(n, real=True)
    f = sfft.rfftfreq(nf, 1 / fs)
    amp = np.sqrt(psd_fn(f) * fs * nf / 2.0)
    amp[0] = 0.0
    spec = amp * (rng.standard_normal(len(f)) + 1j * rng.standard_normal(len(f))) / np.sqrt(2)
    return sfft.irfft(spec, nf)[:n]


def simulate(building: Building, env: Environment, placements: list[Placement], duration: float,
             t_start: float, rng: np.random.Generator, interference: InterferenceSet | None = None,
             floor_method: str = "sim") -> list[RawSession]:
    """Simulate one time interval for one building, observed by one or more phones."""
    n_sim = sfft.next_fast_len(int(round(duration * FS_SIM)), real=True)
    n_sim += n_sim % 2
    dur = n_sim / FS_SIM
    nb = int(F_STRUCT_MAX * dur) + 1
    f = np.arange(nb) / dur
    S = env.source_psd(building, f)
    amp = np.sqrt(S * FS_SIM * n_sim / 2.0)
    xi = amp * (rng.standard_normal(S.shape) + 1j * rng.standard_normal(S.shape)) / np.sqrt(2)
    xi[0] = 0.0
    t_grid0 = t_start

    out = []
    for p in placements:
        T = building.transfer(f, p.floor, p.pos)
        spec = np.einsum("fas,fs->fa", T, xi) * p.mount_tf(f)[:, None]
        m = p.model
        fs_true = m.fs_nominal * (1 + m.odr_sigma * float(np.clip(rng.standard_normal(), -2, 2)))
        n_raw = int(dur * fs_true) - 2
        t_true = t_grid0 + np.arange(n_raw) / fs_true
        world = np.empty((n_raw, 3))
        pad = np.zeros(n_sim // 2 + 1, complex)
        grid_t = np.arange(n_sim) / FS_SIM
        for a in range(3):
            pad[:nb] = spec[:, a]
            world[:, a] = np.interp(t_true - t_grid0, grid_t, sfft.irfft(pad, n_sim))
        if interference is not None:
            world += interference.evaluate(t_true, t_grid0)
        world[:, 2] += G0
        dev = world @ p.rotation()            # device components = R^T world
        for a in range(3):
            dev[:, a] += _coloured(rng, n_raw, fs_true, lambda ff, a=a: m.noise_psd(ff, a))
        if m.tick_hz:
            ph = ((t_true - t_grid0) * m.tick_hz) % 1.0 / m.tick_hz
            dev[:, 0] += m.tick_ug * 9.80665e-6 * np.exp(-ph / 0.02)
        dev = np.round(dev / m.lsb) * m.lsb
        offset = float(rng.normal(0, p.sync_sigma))
        ts = t_true + offset + (t_true - t_grid0) * p.drift_ppm * 1e-6 + rng.normal(0, m.ts_jitter, n_raw)
        ts = np.maximum.accumulate(ts)
        meta = {
            "building_id": building.building_id, "contributor": p.contributor, "phone_model": m.name,
            "floor": p.floor, "floor_method": floor_method, "lsb": m.lsb, "sync_source": "sim",
            "sync_sigma_ms": 1e3 * p.sync_sigma, "provenance": "SIM",
            "truth": {"yaw": p.yaw, "mount_f": p.mount_f, "fs_true": fs_true, "sync_offset": offset,
                      "env": env.name, "modes": building.true_modes(),
                      "lines": interference.lines() if interference else []},
        }
        out.append(RawSession(ts, dev, meta))
    return out
