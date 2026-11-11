"""Phone sensor and placement model.

The model profiles below are representative, not measured (label: ASSUMED). Noise densities span the
range published in IMU datasheets and phone studies (docs/references.md). The collector app measures
each real model's noise floor, and those measurements replace these profiles.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

UG = 9.80665e-6  # one micro-g in m/s^2


@dataclass(frozen=True)
class PhoneModel:
    name: str
    noise_ug: float                 # white noise density on horizontal axes, ug/sqrt(Hz)
    corner_hz: float                # 1/f corner frequency
    z_factor: float = 1.4           # vertical axis noise relative to horizontal
    lsb: float = 0.0012             # quantisation step, m/s^2
    fs_nominal: float = 200.0
    odr_sigma: float = 0.015        # relative spread of the true output data rate
    ts_jitter: float = 150e-6       # timestamp jitter, s (1 sigma)
    resonance: tuple[float, float, float] | None = None   # (f, zeta, peak/noise power ratio)
    tick_hz: float | None = None    # periodic housekeeping disturbance
    tick_ug: float = 0.0

    def noise_psd(self, f: np.ndarray, axis: int = 0) -> np.ndarray:
        """One-sided self-noise PSD, (m/s^2)^2/Hz."""
        f = np.maximum(np.asarray(f, float), 1e-3)
        n0 = (self.noise_ug * UG * (self.z_factor if axis == 2 else 1.0)) ** 2
        s = n0 * (1 + self.corner_hz / f)
        if self.resonance is not None:
            fr, zr, ratio = self.resonance
            u = f / fr
            s = s + n0 * ratio * (2 * zr) ** 2 / ((1 - u**2) ** 2 + (2 * zr * u) ** 2)
        return s


PHONE_MODELS = {
    "low": PhoneModel("low", noise_ug=80.0, corner_hz=0.3, lsb=0.0012, fs_nominal=200.0),
    "mid": PhoneModel("mid", noise_ug=150.0, corner_hz=0.7, lsb=0.0024, fs_nominal=200.0),
    "high": PhoneModel("high", noise_ug=300.0, corner_hz=1.5, lsb=0.0096, fs_nominal=100.0),
    # same as "mid" plus a self-noise resonance and a 1 Hz housekeeping tick; used for artefact tests
    "mid_res": PhoneModel("mid_res", noise_ug=150.0, corner_hz=0.7, lsb=0.0024, fs_nominal=200.0,
                          resonance=(2.9, 0.012, 6.0), tick_hz=1.0, tick_ug=40.0),
}


@dataclass
class Placement:
    """One phone lying somewhere in a building for one session."""
    model: PhoneModel
    floor: int
    pos: tuple[float, float] = (0.0, 0.0)   # plan offset from the centre of rigidity, m
    yaw: float = 0.0                        # rad, phone x axis relative to building x axis
    tilt: tuple[float, float] = (0.0, 0.0)  # small rotations about phone x and y, rad
    mount_f: float = 40.0                   # furniture / surface coupling resonance, Hz
    mount_zeta: float = 0.10
    sync_sigma: float = 0.02                # residual UTC offset error, s (1 sigma)
    drift_ppm: float = 1.0                  # residual clock-rate error after correction
    contributor: str = "c0"

    def mount_tf(self, f: np.ndarray) -> np.ndarray:
        r = np.asarray(f, float) / self.mount_f
        return (1 + 2j * self.mount_zeta * r) / (1 - r**2 + 2j * self.mount_zeta * r)

    def rotation(self) -> np.ndarray:
        """Matrix mapping device-frame vectors to the building/world frame."""
        cz, sz = np.cos(self.yaw), np.sin(self.yaw)
        rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1.0]])
        ax, ay = self.tilt
        rx = np.array([[1, 0, 0], [0, np.cos(ax), -np.sin(ax)], [0, np.sin(ax), np.cos(ax)]])
        ry = np.array([[np.cos(ay), 0, np.sin(ay)], [0, 1, 0], [-np.sin(ay), 0, np.cos(ay)]])
        return rz @ ry @ rx


def random_placement(rng: np.random.Generator, model: PhoneModel, floor: int, width=(20.0, 30.0),
                     soft_mount_prob: float = 0.15, sync_sigma: float = 0.02,
                     contributor: str = "c0") -> Placement:
    """Draw a plausible placement: random yaw, a degree or two of tilt, hard or soft surface."""
    soft = rng.random() < soft_mount_prob
    return Placement(
        model=model, floor=floor,
        pos=(float(rng.uniform(-0.4, 0.4) * width[0]), float(rng.uniform(-0.4, 0.4) * width[1])),
        yaw=float(rng.uniform(0, 2 * np.pi)),
        tilt=(float(rng.normal(0, 0.02)), float(rng.normal(0, 0.02))),
        mount_f=float(rng.uniform(4, 9) if soft else rng.uniform(25, 60)),
        mount_zeta=float(rng.uniform(0.12, 0.25) if soft else rng.uniform(0.05, 0.12)),
        sync_sigma=sync_sigma, drift_ppm=float(abs(rng.normal(0, 1.0))), contributor=contributor)
