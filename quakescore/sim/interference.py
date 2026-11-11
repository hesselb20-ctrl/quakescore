"""Non-structural vibration sources, evaluated analytically at arbitrary sample times.

Every source returns floor acceleration in the building frame, shape (n, 3), in m/s^2. Each source
also reports the frequencies it contaminates so that test sets can be labelled.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

UG = 9.80665e-6


def _duty(t: np.ndarray, t0: float, period: float, on_fraction: float, phase: float) -> np.ndarray:
    """Smooth on/off gate with the given period and duty cycle."""
    x = ((t - t0) / period + phase) % 1.0
    edge = 0.02
    up = np.clip(x / edge, 0, 1)
    down = np.clip((on_fraction - x) / edge, 0, 1)
    return np.minimum(up, down)


@dataclass
class Tone:
    """Rotating machinery (HVAC fan, pump, compressor): a steady line with slight wander."""
    freq: float
    amp_ug: float
    direction: tuple[float, float, float] = (0.7, 0.5, 0.5)
    wander: float = 2e-4            # relative slow frequency wander
    duty_period: float = 0.0        # seconds; 0 means always on
    duty_on: float = 1.0
    phase: float = 0.0
    kind: str = "hvac"

    def evaluate(self, t: np.ndarray, t0: float) -> np.ndarray:
        tau = t - t0
        ph = 2 * np.pi * self.freq * (tau + self.wander * 600 / (2 * np.pi) * np.sin(2 * np.pi * tau / 600 + self.phase))
        s = self.amp_ug * UG * np.sin(ph + self.phase)
        if self.duty_period > 0:
            s = s * _duty(t, t0, self.duty_period, self.duty_on, self.phase / (2 * np.pi))
        return s[:, None] * np.asarray(self.direction)[None, :]

    def lines(self) -> list[tuple[float, str]]:
        return [(self.freq, self.kind)]


@dataclass
class WashingMachine:
    """Tumble phase near 0.8-1 Hz with harmonics, then spin at 8-20 Hz. Intermittent."""
    start: float                    # seconds after session start
    tumble_hz: float = 0.85
    spin_hz: float = 13.3
    amp_ug: float = 120.0
    wash_s: float = 2400.0
    spin_s: float = 480.0
    phase: float = 0.3

    def evaluate(self, t: np.ndarray, t0: float) -> np.ndarray:
        tau = t - t0 - self.start
        out = np.zeros((len(t), 3))
        wash = (tau >= 0) & (tau < self.wash_s)
        if wash.any():
            tw = tau[wash]
            gate = _duty(tw, 0.0, 24.0, 0.6, 0.0)
            s = sum(np.sin(2 * np.pi * self.tumble_hz * h * tw + self.phase * h) / h for h in (1, 2, 3))
            out[wash, 0] = self.amp_ug * UG * gate * s
            out[wash, 2] = 0.6 * out[wash, 0]
        spin = (tau >= self.wash_s) & (tau < self.wash_s + self.spin_s)
        if spin.any():
            ts = tau[spin] - self.wash_s
            ramp = np.clip(ts / 60.0, 0, 1)
            phase = 2 * np.pi * self.spin_hz * (ts * ramp - np.where(ts < 60, ts * ramp / 2, 30.0))
            out[spin, 1] = 2.5 * self.amp_ug * UG * np.sin(phase)
            out[spin, 2] = 0.8 * out[spin, 1]
        return out

    def lines(self) -> list[tuple[float, str]]:
        return [(self.tumble_hz * h, "appliance") for h in (1, 2, 3)] + [(self.spin_hz, "appliance")]


@dataclass
class Elevator:
    """Runs of 8-25 s: a narrowband rumble from guide rails and machine, plus start/stop jolts."""
    runs: np.ndarray                # (n_runs, 2) start time after session start and duration
    rumble_hz: float = 3.4
    amp_ug: float = 250.0
    seed: int = 0

    def evaluate(self, t: np.ndarray, t0: float) -> np.ndarray:
        out = np.zeros((len(t), 3))
        tau = t - t0
        rng = np.random.default_rng(self.seed)
        for start, dur in self.runs:
            lo, hi = np.searchsorted(tau, [start, start + dur])
            if hi <= lo:
                continue
            tr = tau[lo:hi] - start
            env = np.sin(np.pi * tr / dur) ** 0.5
            sig = np.zeros(hi - lo)
            for _ in range(6):   # narrowband random process as a sum of nearby sinusoids
                fr = self.rumble_hz * (1 + rng.normal(0, 0.03))
                sig += rng.normal() * np.sin(2 * np.pi * fr * tr + rng.uniform(0, 2 * np.pi))
            jolt = np.exp(-tr / 0.4) * np.sin(2 * np.pi * 6.0 * tr) + \
                np.exp(-np.maximum(dur - tr, 0) / 0.4) * np.sin(2 * np.pi * 6.0 * (dur - tr))
            out[lo:hi, 0] += self.amp_ug * UG * (env * sig / 2.4 + 2.0 * jolt)
            out[lo:hi, 2] += 0.7 * self.amp_ug * UG * (env * sig / 2.4 + 3.0 * jolt)
        return out

    def lines(self) -> list[tuple[float, str]]:
        return [(self.rumble_hz, "elevator")]


@dataclass
class Footsteps:
    """Somebody walking near the phone: short impulses that the stationarity gate should remove."""
    episodes: np.ndarray            # (n, 2) start and duration
    pace_hz: float = 1.8
    amp_ug: float = 3000.0

    def evaluate(self, t: np.ndarray, t0: float) -> np.ndarray:
        out = np.zeros((len(t), 3))
        tau = t - t0
        for start, dur in self.episodes:
            lo, hi = np.searchsorted(tau, [start, start + dur])
            if hi <= lo:
                continue
            tr = tau[lo:hi] - start
            ph = (tr * self.pace_hz) % 1.0 / self.pace_hz
            pulse = np.exp(-ph / 0.03) * np.sin(2 * np.pi * 18.0 * ph)
            out[lo:hi, 2] += self.amp_ug * UG * pulse
            out[lo:hi, 0] += 0.3 * self.amp_ug * UG * pulse
        return out

    def lines(self) -> list[tuple[float, str]]:
        return []


@dataclass
class InterferenceSet:
    sources: list = field(default_factory=list)

    def evaluate(self, t: np.ndarray, t0: float) -> np.ndarray:
        out = np.zeros((len(t), 3))
        for s in self.sources:
            out += s.evaluate(t, t0)
        return out

    def lines(self) -> list[tuple[float, str]]:
        return [ln for s in self.sources for ln in s.lines()]


def random_interference(rng: np.random.Generator, duration: float, level: float = 1.0,
                        hvac: bool = True, elevator: bool = True, appliance: bool = True,
                        mains_alias: bool = True, footsteps: bool = True) -> InterferenceSet:
    """Draw a plausible contaminated night for one building-session."""
    src: list = []
    if hvac:
        for _ in range(int(rng.integers(1, 4))):
            f = float(rng.choice([rng.uniform(0.9, 4.5), rng.uniform(9, 24), rng.uniform(24.2, 29.8)]))
            cyc = rng.random() < 0.5
            src.append(Tone(f, float(level * rng.uniform(30, 300)), tuple(rng.uniform(0.2, 1, 3)),
                            duty_period=float(rng.uniform(600, 2400)) if cyc else 0.0,
                            duty_on=float(rng.uniform(0.3, 0.7)), phase=float(rng.uniform(0, 6.28))))
    if mains_alias:
        f = float(rng.choice([50.0, 60.0, 100.0]) * (1 + rng.normal(0, 2e-4)))
        src.append(Tone(f, float(level * rng.uniform(100, 600)), (0.5, 0.5, 0.7),
                        phase=float(rng.uniform(0, 6.28)), kind="mains"))
    if elevator and rng.random() < 0.7:
        n = int(rng.integers(3, 15))
        runs = np.stack([np.sort(rng.uniform(0, duration - 30, n)), rng.uniform(8, 25, n)], 1)
        src.append(Elevator(runs, rumble_hz=float(rng.uniform(2.0, 6.0)),
                            amp_ug=float(level * rng.uniform(100, 500)), seed=int(rng.integers(1 << 30))))
    if appliance and rng.random() < 0.4:
        src.append(WashingMachine(start=float(rng.uniform(0, max(duration - 3000, 1))),
                                  tumble_hz=float(rng.uniform(0.7, 1.0)), spin_hz=float(rng.uniform(9, 20)),
                                  amp_ug=float(level * rng.uniform(40, 200)), phase=float(rng.uniform(0, 6.28))))
    if footsteps:
        n = int(rng.integers(0, 6))
        if n:
            ep = np.stack([np.sort(rng.uniform(0, duration - 20, n)), rng.uniform(4, 15, n)], 1)
            src.append(Footsteps(ep, pace_hz=float(rng.uniform(1.5, 2.1)), amp_ug=float(rng.uniform(1500, 6000))))
    return InterferenceSet(src)


@dataclass
class BuildingNoise:
    """Machinery that belongs to a building and therefore recurs in every session recorded there."""
    hvac: list[tuple[float, float, bool]] = field(default_factory=list)    # (Hz, ug, duty-cycled)
    elevator_hz: float | None = None
    elevator_ug: float = 250.0
    mains_hz: float = 50.0

    @staticmethod
    def draw(rng: np.random.Generator, level: float = 1.0) -> "BuildingNoise":
        hvac = []
        for _ in range(int(rng.integers(1, 4))):
            f = float(rng.choice([rng.uniform(0.9, 4.5), rng.uniform(5, 12), rng.uniform(12, 24), rng.uniform(24.2, 29.8)]))
            hvac.append((f, float(level * rng.uniform(30, 300)), bool(rng.random() < 0.5)))
        elev = float(rng.uniform(2.0, 6.0)) if rng.random() < 0.6 else None
        return BuildingNoise(hvac, elev, float(level * rng.uniform(100, 500)), float(rng.choice([50.0, 60.0])))

    def session(self, rng: np.random.Generator, duration: float, appliance_prob: float = 0.3) -> InterferenceSet:
        """Instantiate one night: same machines, slightly different speeds, new schedules."""
        src: list = []
        for f, amp, cyc in self.hvac:
            src.append(Tone(f * (1 + rng.normal(0, 0.003)), amp * float(rng.uniform(0.6, 1.4)), tuple(rng.uniform(0.2, 1, 3)),
                            duty_period=float(rng.uniform(600, 2400)) if cyc else 0.0,
                            duty_on=float(rng.uniform(0.3, 0.7)), phase=float(rng.uniform(0, 6.28))))
        src.append(Tone(self.mains_hz * float(rng.choice([1.0, 2.0])) * (1 + rng.normal(0, 2e-4)), float(rng.uniform(100, 600)),
                        (0.5, 0.5, 0.7), phase=float(rng.uniform(0, 6.28)), kind="mains"))
        if self.elevator_hz is not None:
            n = int(rng.integers(3, 15))
            runs = np.stack([np.sort(rng.uniform(0, duration - 30, n)), rng.uniform(8, 25, n)], 1)
            src.append(Elevator(runs, self.elevator_hz, self.elevator_ug * float(rng.uniform(0.7, 1.3)), int(rng.integers(1 << 30))))
        if rng.random() < appliance_prob:
            src.append(WashingMachine(start=float(rng.uniform(0, max(duration - 3000, 1))), tumble_hz=float(rng.uniform(0.7, 1.0)),
                                      spin_hz=float(rng.uniform(9, 20)), amp_ug=float(rng.uniform(40, 200)),
                                      phase=float(rng.uniform(0, 6.28))))
        n = int(rng.integers(0, 6))
        if n:
            ep = np.stack([np.sort(rng.uniform(0, duration - 20, n)), rng.uniform(4, 15, n)], 1)
            src.append(Footsteps(ep, pace_hz=float(rng.uniform(1.5, 2.1)), amp_ug=float(rng.uniform(1500, 6000))))
        return InterferenceSet(src)
