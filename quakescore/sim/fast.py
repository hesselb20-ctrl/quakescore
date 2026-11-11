"""Fast spectral-domain session simulator.

Instead of generating hours of samples, draw each session's averaged cross-spectral matrix from its
sampling distribution (complex Wishart with K degrees of freedom around the analytic expectation).
Gaussian sources only: no quantisation, jitter, gating losses or interference. It is validated
against the time-domain path in experiments/m1_validate_fast.py and is used for large sweeps.
"""
from __future__ import annotations

import numpy as np

from ..features import BANDS, NBINS, NFFT, BandFeatures, SessionFeatures, droop
from .building import Building
from .excitation import Environment
from .phone import Placement

OVERSAMPLE = 8
_OVERLAP_DOF = 1.0 / (1.0 + 2.0 * (1.0 / 6.0) ** 2)   # effective windows per window, Hann at 50% overlap


def _hann_kernel() -> np.ndarray:
    """Power response of the Hann window sampled every 1/OVERSAMPLE bin over +-3 bins."""
    nu = np.arange(-3 * OVERSAMPLE, 3 * OVERSAMPLE + 1) / OVERSAMPLE
    w = 0.5 * np.sinc(nu) - 0.25 * np.sinc(nu - 1) - 0.25 * np.sinc(nu + 1)
    k = w**2
    return k / k.sum()


_KERNEL = _hann_kernel()


class FastSite:
    """Caches the building-frame response for one (building, environment, floor, position).

    Sessions at the same site differ only in yaw, furniture coupling and phone model, which are
    cheap to apply, so large sweeps reuse one site for many sessions.
    """

    def __init__(self, building: Building, env: Environment, floor: int,
                 pos: tuple[float, float] = (0.0, 0.0), bands: tuple[str, ...] = ("L", "M", "H")):
        self.building, self.env, self.floor, self.pos = building, env, floor, pos
        self.fa: dict[str, np.ndarray] = {}
        self.gw: dict[str, np.ndarray] = {}
        pad = 3 * OVERSAMPLE
        for band in bands:
            df = BANDS[band]["fs"] / NFFT
            fa = np.abs(np.arange(-pad, (NBINS - 1) * OVERSAMPLE + pad + 1) / OVERSAMPLE) * df
            T = building.transfer(fa, floor, pos)
            S = env.source_psd(building, fa)
            self.fa[band] = fa
            self.gw[band] = np.einsum("fas,fs,fbs->fab", T, S, T.conj())

    def expected(self, band: str, p: Placement) -> np.ndarray:
        """Expected window-averaged 3x3 CSD in the phone's level frame, shape (NBINS, 3, 3)."""
        fa = self.fa[band]
        G = self.gw[band] * (np.abs(p.mount_tf(fa)) ** 2)[:, None, None]
        c, s = np.cos(p.yaw), np.sin(p.yaw)
        R = np.array([[c, s, 0], [-s, c, 0], [0, 0, 1.0]])          # world -> level frame
        G = np.einsum("ai,fij,bj->fab", R, G, R)
        for a in range(3):
            G[:, a, a] += p.model.noise_psd(fa, a)
        G *= droop(fa, p.model.fs_nominal)[:, None, None]
        out = np.empty((NBINS, 3, 3), complex)                       # leakage, then sample at bins
        for a in range(3):
            for b in range(a, 3):
                sm = np.convolve(G[:, a, b], _KERNEL, mode="valid")[::OVERSAMPLE][:NBINS]
                out[:, a, b] = sm
                out[:, b, a] = sm.conj()
        out[0] = out[1]
        return out


def expected_csd(building: Building, env: Environment, p: Placement, band: str) -> np.ndarray:
    return FastSite(building, env, p.floor, p.pos, (band,)).expected(band, p)


def _wishart(rng: np.random.Generator, mean: np.ndarray, k_eff: float) -> np.ndarray:
    """Sample mean-normalised complex Wishart matrices per bin (Bartlett decomposition)."""
    n = mean.shape[0]
    L = np.linalg.cholesky(mean + 1e-30 * np.eye(3)[None])
    A = np.zeros((n, 3, 3), complex)
    for i in range(3):
        A[:, i, i] = np.sqrt(rng.gamma(max(k_eff - i, 0.5), 1.0, n))
        for j in range(i):
            A[:, i, j] = (rng.standard_normal(n) + 1j * rng.standard_normal(n)) / np.sqrt(2)
    LA = L @ A
    return LA @ LA.conj().transpose(0, 2, 1) / k_eff


def windows_in(duration: float, band: str, accept: float = 0.97) -> int:
    fs = BANDS[band]["fs"]
    return max(int(accept * (duration * fs - NFFT) / (NFFT // 2)), 0)


def simulate_features(building: Building, env: Environment, p: Placement, duration: float,
                      t_start: float, rng: np.random.Generator, session_id: str = "s",
                      site: FastSite | None = None, temp_c: float | None = None,
                      bands: tuple[str, ...] = ("L", "M", "H")) -> SessionFeatures:
    """Draw one session's uploaded features. Pass a FastSite to reuse the building response."""
    if site is None:
        site = FastSite(building, env, p.floor, p.pos, bands)
    out = {}
    for band in bands:
        k = windows_in(duration, band)
        mean = site.expected(band, p)
        if k < 3:
            out[band] = BandFeatures(0, np.zeros((NBINS, 3, 3), np.complex64), np.zeros((NBINS, 3), np.float32))
            continue
        k_eff = max(k * _OVERLAP_DOF, 3.0)
        csd = _wishart(rng, mean, k_eff)
        diag = np.stack([csd[:, a, a].real for a in range(3)], 1)
        cv2 = 1.0 + rng.normal(0, np.sqrt(8.0 / k_eff), diag.shape)
        out[band] = BandFeatures(k, csd.astype(np.complex64), (diag**2 * (1 + cv2)).astype(np.float32))
    return SessionFeatures(
        session_id=session_id, building_id=building.building_id, contributor=p.contributor,
        phone_model=p.model.name, floor=p.floor, floor_method="sim", t_start=float(60 * round(t_start / 60)),
        duration=duration, fs_raw=p.model.fs_nominal, lsb=p.model.lsb, sync_source="sim",
        sync_sigma_ms=1e3 * p.sync_sigma, accept_fraction=0.97, bands=out, temp_c=temp_c, provenance="SIM",
        truth={"yaw": p.yaw, "mount_f": p.mount_f, "env": env.name, "modes": building.true_modes(), "lines": []})


def simulate_sync_frames(building: Building, env: Environment, placements: list[Placement], band: str,
                         f_range: tuple[float, float], n_windows: int, rng: np.random.Generator,
                         ) -> tuple[np.ndarray, np.ndarray]:
    """Simultaneous window spectra for several phones (tier B), restricted to a frequency range.

    Returns (freqs, X) with X of shape (n_windows, n_f, n_phones, 3) in each phone's level frame.
    Phones share the building's sources, so their spectra are coherent; sensor noise is independent
    and each phone carries its own residual clock offset.
    """
    fs = BANDS[band]["fs"]
    f_all = np.arange(NBINS) * fs / NFFT
    sel = (f_all >= f_range[0]) & (f_all <= f_range[1])
    f = f_all[sel]
    S = env.source_psd(building, f)
    xi = np.sqrt(S)[None] * (rng.standard_normal((n_windows,) + S.shape)
                             + 1j * rng.standard_normal((n_windows,) + S.shape)) / np.sqrt(2)
    X = np.empty((n_windows, len(f), len(placements), 3), complex)
    for ip, p in enumerate(placements):
        T = building.transfer(f, p.floor, p.pos) * p.mount_tf(f)[:, None, None]
        c, s = np.cos(p.yaw), np.sin(p.yaw)
        R = np.array([[c, s, 0], [-s, c, 0], [0, 0, 1.0]])
        x = np.einsum("ai,fis,kfs->kfa", R, T, xi)
        offset = rng.normal(0, p.sync_sigma)
        x *= np.exp(-2j * np.pi * f * offset)[None, :, None]
        for a in range(3):
            sd = np.sqrt(p.model.noise_psd(f, a))
            x[:, :, a] += sd[None] * (rng.standard_normal((n_windows, len(f)))
                                      + 1j * rng.standard_normal((n_windows, len(f)))) / np.sqrt(2)
        X[:, :, ip, :] = x
    return f, X
