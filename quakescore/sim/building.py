"""Lumped-mass shear-building model with two translational directions and torsion.

Each direction is an independent chain of storey masses and storey stiffnesses. The response at a
floor is assembled by modal superposition in the frequency domain, which is exact for a linear
structure under stationary forcing.

Source ordering used throughout the simulator:
    [ground_x, ground_y, ground_z, wind_x mode 1..nx, wind_y mode 1..ny, torque mode 1..nt]
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

G0 = 9.80665
DIRS = ("x", "y", "t")


def chain_modes(m: np.ndarray, k: np.ndarray):
    """Modes of a fixed-base chain. k[i] is the stiffness of the storey below mass i.

    Returns frequencies (Hz, ascending), shapes phi (n_floor, n_mode) normalised to +1 at the roof,
    modal masses and base-excitation participation factors.
    """
    n = len(m)
    K = np.zeros((n, n))
    for i in range(n):
        K[i, i] = k[i] + (k[i + 1] if i + 1 < n else 0.0)
        if i + 1 < n:
            K[i, i + 1] = K[i + 1, i] = -k[i + 1]
    ms = 1.0 / np.sqrt(m)
    w2, v = np.linalg.eigh(K * ms[:, None] * ms[None, :])
    phi = v * ms[:, None]
    phi = phi / phi[-1, :]
    mm = (m[:, None] * phi**2).sum(0)
    gamma = (m[:, None] * phi).sum(0) / mm
    return np.sqrt(np.maximum(w2, 0.0)) / (2 * np.pi), phi, mm, gamma


@dataclass
class ModalSet:
    f: np.ndarray       # (n_mode,) Hz
    zeta: np.ndarray    # (n_mode,)
    phi: np.ndarray     # (n_floor, n_mode), roof = 1
    mm: np.ndarray      # modal mass (kg, or kg m^2 for torsion)
    gamma: np.ndarray   # participation factor


@dataclass
class Building:
    n_storeys: int
    f1: tuple[float, float, float]                  # target fundamental frequency x, y, torsion (Hz)
    zeta1: tuple[float, float, float] = (0.02, 0.02, 0.02)
    storey_height: float = 3.3
    width: tuple[float, float] = (20.0, 30.0)       # plan dimensions along x and y (m)
    mass_per_area: float = 1000.0                   # kg/m^2 per floor
    taper: float = 0.5                              # stiffness at the top relative to the base
    k_storey: np.ndarray | None = None              # per-storey multipliers applied after tuning
    k_scale: float = 1.0                            # global stiffness multiplier (damage, softening)
    fmax: float = 25.0
    max_modes: int = 6
    building_id: str = "sim"
    modes: dict[str, ModalSet] = field(init=False, repr=False)

    def __post_init__(self):
        n = self.n_storeys
        area = self.width[0] * self.width[1]
        m = np.full(n, self.mass_per_area * area)
        rg2 = (self.width[0] ** 2 + self.width[1] ** 2) / 12.0
        base = np.linspace(1.0, self.taper, n)
        mult = np.ones(n) if self.k_storey is None else np.asarray(self.k_storey, float)
        self.modes = {}
        for d, f_target, z1 in zip(DIRS, self.f1, self.zeta1):
            mass = m * rg2 if d == "t" else m
            f0, _, _, _ = chain_modes(mass, base)
            k = base * (f_target / f0[0]) ** 2          # tuned so the undamaged chain hits f_target
            f, phi, mm, gamma = chain_modes(mass, k * mult * self.k_scale)
            keep = (f < self.fmax)
            keep[self.max_modes:] = False
            keep[0] = True
            f, phi, mm, gamma = f[keep], phi[:, keep], mm[keep], gamma[keep]
            zeta = np.minimum(z1 * (f / f[0]) ** 0.25, 0.08)
            self.modes[d] = ModalSet(f, zeta, phi, mm, gamma)

    # ------------------------------------------------------------------ properties
    @property
    def height(self) -> float:
        return self.n_storeys * self.storey_height

    @property
    def floor_heights(self) -> np.ndarray:
        return self.storey_height * np.arange(1, self.n_storeys + 1)

    @property
    def n_sources(self) -> int:
        return 3 + sum(len(self.modes[d].f) for d in DIRS)

    def source_labels(self) -> list[str]:
        lab = ["ground_x", "ground_y", "ground_z"]
        for d in DIRS:
            lab += [f"wind_{d}{j + 1}" for j in range(len(self.modes[d].f))]
        return lab

    def true_modes(self) -> list[dict]:
        """Ground-truth list of translational and torsional modes, sorted by frequency."""
        out = []
        for d in DIRS:
            ms = self.modes[d]
            for j, (f, z) in enumerate(zip(ms.f, ms.zeta)):
                out.append({"dir": d, "order": j + 1, "f": float(f), "zeta": float(z)})
        return sorted(out, key=lambda r: r["f"])

    # ------------------------------------------------------------------ transfer functions
    def transfer(self, f: np.ndarray, floor: int, pos: tuple[float, float] = (0.0, 0.0),
                 slab_f: float = 11.0, slab_zeta: float = 0.04) -> np.ndarray:
        """Absolute-acceleration transfer matrix T[f, axis, source] at a floor (0 = ground).

        Ground sources are accelerations; wind sources are modal forces (N) or torques (N m).
        `pos` is the phone's plan offset from the centre of rigidity (m).
        """
        f = np.asarray(f, float)
        w = 2 * np.pi * f
        T = np.zeros((len(f), 3, self.n_sources), complex)
        T[:, 0, 0] = 1.0
        T[:, 1, 1] = 1.0
        r = f / slab_f
        T[:, 2, 2] = (1 + 2j * slab_zeta * r) / (1 - r**2 + 2j * slab_zeta * r) if floor > 0 else 1.0
        if floor <= 0:
            return T
        i = min(floor, self.n_storeys) - 1
        col = 3
        for d in DIRS:
            ms = self.modes[d]
            for j in range(len(ms.f)):
                wj = 2 * np.pi * ms.f[j]
                den = wj**2 - w**2 + 2j * ms.zeta[j] * wj * w
                acc_per_force = -(w**2) / (ms.mm[j] * den) * ms.phi[i, j]
                if d == "x":
                    T[:, 0, 0] += ms.phi[i, j] * ms.gamma[j] * w**2 / den
                    T[:, 0, col] = acc_per_force
                elif d == "y":
                    T[:, 1, 1] += ms.phi[i, j] * ms.gamma[j] * w**2 / den
                    T[:, 1, col] = acc_per_force
                else:
                    T[:, 0, col] = -pos[1] * acc_per_force
                    T[:, 1, col] = pos[0] * acc_per_force
                col += 1
        return T

    def damaged(self, k_scale: float) -> "Building":
        """Copy with global stiffness multiplied by k_scale (frequencies scale with its square root)."""
        return Building(self.n_storeys, self.f1, self.zeta1, self.storey_height, self.width,
                        self.mass_per_area, self.taper, self.k_storey, self.k_scale * k_scale,
                        self.fmax, self.max_modes, self.building_id)


def typical_f1(n_storeys: int, storey_height: float = 3.3, coeff: float = 0.020) -> float:
    """Ambient-level fundamental frequency from T = coeff * H. Used only to seed simulations."""
    return 1.0 / (coeff * n_storeys * storey_height)


def make_building(n_storeys: int, rng: np.random.Generator | None = None, zeta: float | None = None,
                  scatter: float = 0.0, **kw) -> Building:
    """Convenience constructor: plausible frequencies in x, y and torsion for a given height."""
    f1 = typical_f1(n_storeys, kw.get("storey_height", 3.3))
    if rng is not None and scatter > 0:
        f1 *= float(np.exp(rng.normal(0, scatter)))
    ry = 1.18 if rng is None else float(rng.uniform(1.08, 1.30))
    rt = 1.45 if rng is None else float(rng.uniform(1.30, 1.65))
    if zeta is None:
        zeta = float(np.clip(0.035 - 0.0006 * n_storeys, 0.01, 0.035))
    return Building(n_storeys, (f1, f1 * ry, f1 * rt), (zeta, zeta, zeta), **kw)
