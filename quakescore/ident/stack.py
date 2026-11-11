"""Stack session spectra per building and detect candidate peaks with a matched filter."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import numpy as np

from ..features import BANDS, NBINS, SessionFeatures, band_freqs, droop

ZETA_GRID = (0.004, 0.008, 0.015, 0.025, 0.04, 0.07)


@dataclass
class Stack:
    """Per-session horizontal trace spectra of one building in one band."""
    band: str
    f: np.ndarray
    traces: np.ndarray        # (n_sessions, NBINS)
    k: np.ndarray             # (n_sessions,) windows per session
    w: np.ndarray             # (n_sessions,) stacking weights
    tone: np.ndarray          # (n_sessions, NBINS) per-session tone statistic
    sessions: list[SessionFeatures]
    ztraces: np.ndarray | None = None   # (n_sessions, NBINS) vertical PSD per session

    @property
    def n(self) -> int:
        return len(self.k)

    def mean(self, idx: np.ndarray | None = None) -> np.ndarray:
        """Weighted mean trace; idx resamples sessions (bootstrap)."""
        w, t = (self.w, self.traces) if idx is None else (self.w[idx], self.traces[idx])
        return (w[:, None] * t).sum(0) / w.sum()

    def tone_mean(self) -> np.ndarray:
        """Power-weighted mean of the per-session tone statistic.

        Weighting by each session's contribution to the stacked power means that a line present in
        only some sessions is judged on those sessions, not diluted by the ones without it.
        """
        wp = self.w[:, None] * self.traces
        return (wp * self.tone).sum(0) / np.maximum(wp.sum(0), 1e-300)


def build_stack(sessions: list[SessionFeatures], band: str) -> Stack | None:
    """Inverse-variance weighted stack: w = K / B^2 with B the session's median level in band."""
    f = band_freqs(band)
    lo, hi = BANDS[band]["search"]
    sel = (f >= lo) & (f <= hi)
    use = [s for s in sessions if band in s.bands and s.bands[band].k >= 3]
    if not use:
        return None
    traces = np.stack([s.trace(band) for s in use])
    k = np.array([s.bands[band].k for s in use], float)
    level = np.median(traces[:, sel], 1)
    w = k / np.maximum(level, 1e-300) ** 2
    tone = np.stack([s.tone_stat(band) for s in use])
    ztraces = np.stack([sess.bands[band].csd[:, 2, 2].real / droop(f, sess.fs_raw) for sess in use])
    return Stack(band, f, traces, k, w / w.sum(), tone, use, ztraces)


PASSBAND = 0.8   # usable fraction of each band's Nyquist (the decimation filter rolls off above it)


def baseline(f: np.ndarray, y: np.ndarray, frac: float = 0.30, n_anchor: int = 72) -> np.ndarray:
    """Robust smooth baseline: running median over a +-frac window in log-frequency.

    Only the band's passband is used. Outside it the baseline equals the data, so the excess is zero.
    """
    valid = (f > 0) & (f <= PASSBAND * f[-1])
    fv, yv = f[valid], y[valid]
    fa = np.exp(np.linspace(np.log(fv[0]), np.log(fv[-1]), n_anchor))
    lo = np.searchsorted(fv, fa / (1 + frac))
    hi = np.searchsorted(fv, fa * (1 + frac), side="right")
    med = np.array([np.median(yv[a:max(b, a + 2)]) for a, b in zip(lo, hi)])
    out = np.array(y, float)
    out[valid] = np.exp(np.interp(np.log(fv), np.log(fa), np.log(np.maximum(med, 1e-300))))
    return np.where(out > 0, out, 1e-300)


def sdof_shape(u: np.ndarray, zeta: float) -> np.ndarray:
    """Single-mode power response normalised to 1 at resonance; u = f / f0."""
    return (2 * zeta) ** 2 / ((1 - u**2) ** 2 + (2 * zeta * u) ** 2)


@lru_cache(maxsize=None)
def _templates(band: str, zeta: float) -> tuple[np.ndarray, np.ndarray]:
    """Zero-mean unit-norm matched-filter rows for every candidate centre bin in the search range."""
    f = band_freqs(band)
    lo, hi = BANDS[band]["search"]
    centres = np.flatnonzero((f >= lo) & (f <= hi))
    df = f[1]
    A = np.zeros((len(centres), NBINS), np.float32)
    for r, c in enumerate(centres):
        h = max(5 * zeta * f[c], 4 * df)
        a, b = np.searchsorted(f, [f[c] - h, min(f[c] + h, PASSBAND * f[-1])])
        a, b = max(a, 1), min(b, NBINS)
        t = sdof_shape(f[a:b] / f[c], zeta)
        t = t - t.mean()
        A[r, a:b] = t / np.sqrt((t**2).sum())
    return centres, A


@dataclass
class Candidate:
    band: str
    f: float
    zeta: float
    z: float


def whiten(f: np.ndarray, t: np.ndarray, band: str) -> tuple[np.ndarray, np.ndarray, float]:
    """Return (excess ratio r = T/B - 1, baseline B, robust noise scale of r)."""
    b = baseline(f, t)
    r = t / b - 1.0
    lo, hi = BANDS[band]["search"]
    sel = (f >= lo * 0.8) & (f <= hi * 1.2)
    sigma = 1.4826 * np.median(np.abs(r[sel] - np.median(r[sel])))
    return r, b, float(max(sigma, 1e-12))


def matched_filter(f: np.ndarray, t: np.ndarray, band: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """z-score of the best damping template at each centre bin. Returns (centres, z, zeta)."""
    r, _, sigma = whiten(f, t, band)
    zs = []
    for zeta in ZETA_GRID:
        centres, A = _templates(band, zeta)
        zs.append(A @ np.clip(r, -1e6, 1e6).astype(np.float32) / sigma)
    zs = np.stack(zs)
    best = zs.argmax(0)
    return centres, zs.max(0), np.asarray(ZETA_GRID)[best]


def detect(stack: Stack, z_min: float = 6.0, idx: np.ndarray | None = None,
           min_sep: float = 0.03) -> list[Candidate]:
    """Candidate peaks in one band, strongest first, with non-maximum suppression."""
    t = stack.mean(idx)
    centres, z, zeta = matched_filter(stack.f, t, stack.band)
    order = np.argsort(-z)
    out: list[Candidate] = []
    for i in order:
        if z[i] < z_min:
            break
        fc = stack.f[centres[i]]
        if any(abs(fc / c.f - 1) < max(min_sep, 3 * c.zeta) for c in out):
            continue
        out.append(Candidate(stack.band, float(fc), float(zeta[i]), float(z[i])))
    return out


def merge_bands(cands: list[Candidate]) -> list[Candidate]:
    """Where two bands report the same peak, keep the one whose home range contains it."""
    cands = sorted(cands, key=lambda c: c.f)
    keep: list[Candidate] = []
    for c in cands:
        dup = next((k for k in keep if abs(k.f / c.f - 1) < 0.04), None)
        if dup is None:
            keep.append(c)
            continue
        lo, hi = BANDS[c.band]["home"]
        if lo <= c.f < hi:
            keep[keep.index(dup)] = c
    return keep
