"""Ambient forcing: ground microtremor and wind.

Levels are scenario parameters (label: ASSUMED). They are the largest unknown in the whole model
and are what field sessions must calibrate. See docs/references.md for the published ranges the
presets were chosen from.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .building import DIRS, Building

RHO_AIR = 1.25


@dataclass(frozen=True)
class Environment:
    name: str = "typical"
    ground_db: float = -100.0      # plateau level, dB re 1 (m/s^2)^2/Hz, 1-20 Hz
    wind_u10: float = 3.0          # mean wind speed at 10 m (m/s)
    turb_intensity: float = 0.25   # sigma_u / U10
    wind_alpha: float = 0.25       # power-law exponent (urban)
    length_scale: float = 100.0    # turbulence integral scale (m)
    coh_decay: float = 10.0        # vertical coherence decay constant
    cd: float = 1.3
    ecc: float = 0.08              # torque eccentricity as a fraction of the wind-facing width
    microseism_db: float = -125.0  # level of the secondary microseism bump near 0.2 Hz

    # -------------------------------------------------------------- ground
    def ground_psd(self, f: np.ndarray) -> np.ndarray:
        """One-sided horizontal ground acceleration PSD, (m/s^2)^2/Hz."""
        f = np.maximum(np.asarray(f, float), 1e-4)
        plateau = 10 ** (self.ground_db / 10)
        cultural = plateau * np.where(f < 1.0, f**2, 1.0)
        micro = 10 ** (self.microseism_db / 10) * np.exp(-0.5 * (np.log(f / 0.2) / 0.35) ** 2)
        return cultural + micro

    # -------------------------------------------------------------- wind
    def wind_speed(self, z: np.ndarray) -> np.ndarray:
        return self.wind_u10 * (np.maximum(z, 5.0) / 10.0) ** self.wind_alpha

    def _karman(self, f: np.ndarray, u_ref: float) -> np.ndarray:
        """Normalised along-wind turbulence spectrum S_u(f)/sigma_u^2 (per Hz)."""
        x = f * self.length_scale / u_ref
        return 4 * (self.length_scale / u_ref) / (1 + 70.8 * x**2) ** (5 / 6)

    def wind_modal_psd(self, b: Building, f: np.ndarray) -> dict[str, np.ndarray]:
        """Modal force (x, y) and modal torque (t) PSDs, shape (n_mode, n_f) per direction."""
        f = np.maximum(np.asarray(f, float), 1e-4)
        z = b.floor_heights
        u = self.wind_speed(z)
        u_ref = float(self.wind_speed(np.array([2 * b.height / 3]))[0])
        sigma_u = self.turb_intensity * self.wind_u10
        fc = np.logspace(-2.3, np.log10(b.fmax * 1.2), 56)
        dz = np.abs(z[:, None] - z[None, :])
        coh = np.exp(-self.coh_decay * fc[:, None, None] * dz[None] / u_ref)       # (nc, N, N)
        spec = self._karman(f, u_ref)
        out = {}
        for d in DIRS:
            # x-direction motion is driven by pressure on the face of width b.width[1], and vice versa
            face = b.width[1] if d in ("x", "t") else b.width[0]
            scale = 1.0 if d != "y" else 0.7
            sig_f = RHO_AIR * self.cd * face * b.storey_height * u * sigma_u * scale  # N per floor
            if d == "t":
                sig_f = sig_f * self.ecc * face
            adm = 1.0 / (1 + (2 * f * face / u_ref) ** (4 / 3)) ** 2
            ms = b.modes[d]
            psd = np.empty((len(ms.f), len(f)))
            for j in range(len(ms.f)):
                a = ms.phi[:, j] * sig_f
                j2 = np.einsum("i,cik,k->c", a, coh, a)
                psd[j] = np.exp(np.interp(np.log(f), np.log(fc), np.log(j2))) * spec * adm
            out[d] = psd
        return out

    def source_psd(self, b: Building, f: np.ndarray) -> np.ndarray:
        """PSD of every source in simulator ordering, shape (n_f, n_src)."""
        g = self.ground_psd(f)
        cols = [g, g, 0.25 * g]
        wind = self.wind_modal_psd(b, f)
        for d in DIRS:
            cols += list(wind[d])
        s = np.stack(cols, 1)
        s[np.asarray(f) <= 0] = 0.0
        return s


ENVIRONMENTS = {
    "quiet": Environment("quiet", ground_db=-110.0, wind_u10=1.5),
    "typical": Environment("typical", ground_db=-100.0, wind_u10=3.0),
    "energetic": Environment("energetic", ground_db=-90.0, wind_u10=7.0),
}


def response_psd(b: Building, env: Environment, f: np.ndarray, floor: int,
                 pos: tuple[float, float] = (0.0, 0.0)) -> np.ndarray:
    """Analytic 3x3 absolute-acceleration CSD at a floor in the building frame, (n_f, 3, 3)."""
    T = b.transfer(f, floor, pos)
    S = env.source_psd(b, f)
    return np.einsum("fas,fs,fbs->fab", T, S, T.conj())


def roof_rms_ug(b: Building, env: Environment, direction: int = 0) -> float:
    """RMS acceleration at the roof in micro-g, integrated over 0.05-25 Hz (one direction)."""
    f = np.logspace(np.log10(0.05), np.log10(25.0), 6000)
    g = response_psd(b, env, f, b.n_storeys)[:, direction, direction].real
    return float(np.sqrt(np.trapezoid(g, f)) / 9.80665e-6)
