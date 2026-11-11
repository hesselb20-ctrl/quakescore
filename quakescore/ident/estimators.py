"""Modal estimators: spectral curve fit, EFDD, SSI-COV, random decrement and FDD on sync frames.

All frequency-domain estimators work on stacked spectra, because that is all the server ever has.
Random decrement needs a time series and therefore runs on the device.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from scipy import optimize, signal

from ..features import BANDS, NFFT
from .stack import baseline, sdof_shape

_OS = 4  # oversampling of the model grid for leakage smoothing


@lru_cache(maxsize=None)
def _leak_kernel() -> np.ndarray:
    nu = np.arange(-2 * _OS, 2 * _OS + 1) / _OS
    w = 0.5 * np.sinc(nu) - 0.25 * np.sinc(nu - 1) - 0.25 * np.sinc(nu + 1)
    k = w**2
    return k / k.sum()


@lru_cache(maxsize=None)
def window_correlation() -> np.ndarray:
    """Normalised autocorrelation of the Hann window at lags 0..NFFT-1 samples."""
    w = signal.get_window("hann", NFFT, fftbins=True)
    c = signal.fftconvolve(w, w[::-1])[NFFT - 1:]
    return c / c[0]


@dataclass
class ModeEstimate:
    f: float
    zeta: float
    amp: float = np.nan          # peak power above baseline
    snr: float = np.nan          # peak-to-baseline power ratio
    ok: bool = True
    method: str = ""
    colour: float = 1.0          # exponent of the forcing/response slope across the peak
    cost: float = np.nan         # sum of squared deviance residuals of the fit
    nbins: int = 0


def _shape(u: np.ndarray, zeta: float, colour: float) -> np.ndarray:
    return u**colour * sdof_shape(u, zeta)


def peak_model(f: np.ndarray, est: ModeEstimate) -> np.ndarray:
    """Leakage-smoothed model of one fitted peak on a band's bin grid (zero far from the peak)."""
    df = f[1] - f[0]
    pad = 2 * _OS
    ff = np.maximum(np.abs(np.arange(-pad, (len(f) - 1) * _OS + pad + 1) / _OS * df), 1e-6)
    u = ff / est.f
    m = np.where((u > 0.5) & (u < 1.6), est.amp * _shape(np.clip(u, 0.5, 1.6), est.zeta, est.colour), 0.0)
    return np.convolve(m, _leak_kernel(), mode="valid")[::_OS]


# --------------------------------------------------------------------------- curve fit
def curve_fit(f: np.ndarray, t: np.ndarray, peaks: list[tuple[float, float]], target: int = 0,
              base: np.ndarray | None = None, sub: np.ndarray | None = None,
              colour: bool = False, window: tuple[float, float] | None = None) -> list[ModeEstimate]:
    """Whittle-likelihood fit of one or more single-mode shapes plus a power-law baseline.

    `peaks` are (f0, zeta0) starting values, fitted jointly inside one window around peaks[target].
    `sub` is an already-known contribution (other peaks) removed before fitting. With colour=True a
    slope exponent across each peak is fitted too; that matters only when the peak stands well
    above the noise, where the skirts differ between wind and ground excitation. The model is
    smoothed with the Hann leakage kernel before comparison with the data.
    """
    df = f[1] - f[0]
    f0, z0 = peaks[target]
    half = min(max(6 * z0 * f0, 8 * df), 0.25 * f0)
    lo = min([f0 - half] + [p[0] * (1 - 3 * p[1]) for p in peaks])
    hi = max([f0 + half] + [p[0] * (1 + 3 * p[1]) for p in peaks])
    if window is not None:
        lo, hi = window
    a, b = max(int(np.ceil(lo / df)), 1), min(int(np.floor(hi / df)), int(0.8 * (len(f) - 1)))
    if base is None:
        base = baseline(f, t)
    if b - a < 6:
        return [ModeEstimate(p[0], p[1], ok=False, method="fit") for p in peaks]
    y = t[a:b + 1] if sub is None else np.maximum(t[a:b + 1] - sub[a:b + 1], 1e-3 * base[a:b + 1])
    pad = 2 * _OS
    ff = np.maximum(np.abs(np.arange(a * _OS - pad, b * _OS + pad + 1) / _OS * df), 1e-6)
    kern = _leak_kernel()
    b0 = float(np.median(base[a:b + 1]))
    npk = len(peaks)

    def model(x):
        m = np.exp(x[0]) * (ff / f0) ** x[1]
        for j in range(npk):
            q = x[2 + 4 * j:6 + 4 * j]
            m = m + np.exp(q[0]) * _shape(ff / np.exp(q[1]), np.exp(q[2]), q[3])
        return np.convolve(m, kern, mode="valid")[::_OS]

    def resid(x):
        ratio = np.maximum(y / np.maximum(model(x), 1e-300), 1e-12)
        return np.sign(ratio - 1) * np.sqrt(2 * np.maximum(ratio - 1 - np.log(ratio), 0))

    x0, lb, ub = [np.log(b0), 0.0], [np.log(b0) - 4, -8.0], [np.log(b0) + 4, 8.0]
    cl, cu = (-3.0, 5.0) if colour else (1.0 - 1e-9, 1.0 + 1e-9)
    f_lo, f_hi = f[1], 0.8 * f[-1]                      # a mode must stay inside the band's passband
    if any(not (f_lo < fj < f_hi) for fj, _ in peaks):
        return [ModeEstimate(p[0], p[1], ok=False, method="fit") for p in peaks]
    for fj, zj in peaks:
        zj = float(np.clip(zj, 1.2e-3, 0.2))
        i = min(int(round(fj / df)), len(t) - 1)
        amp0 = max(t[i] - (0.0 if sub is None else sub[i]) - base[i], 0.05 * base[i])
        x0 += [np.log(amp0), np.log(fj), np.log(zj), 1.0]
        lb += [np.log(amp0) - 8, np.log(max(fj * (1 - max(3 * zj, 0.02)), 0.5 * fj, 0.999 * f_lo)), np.log(1e-3), cl]
        ub += [np.log(amp0) + 8, np.log(min(fj * (1 + max(3 * zj, 0.02)), 1.5 * fj, 1.001 * f_hi)), np.log(0.25), cu]
    try:
        sol = optimize.least_squares(resid, x0, bounds=(lb, ub), method="trf", x_scale="jac", max_nfev=150)
        x, ok = sol.x, bool(sol.status >= 0 and np.all(np.isfinite(sol.x)))
        cost = float(2 * sol.cost)
    except Exception:
        x, ok, cost = np.array(x0), False, float("nan")
    out = []
    for j in range(npk):
        q = x[2 + 4 * j:6 + 4 * j]
        amp, fj, zj = np.exp(q[:3])
        bj = np.exp(x[0]) * (fj / f0) ** x[1]
        out.append(ModeEstimate(float(fj), float(zj), float(amp), float(amp / bj), ok, "fit", float(q[3]), cost, len(y)))
    return out


# --------------------------------------------------------------------------- shared helper
def _band_correlation(f: np.ndarray, excess: np.ndarray, f0: float, zeta0: float, band: str,
                      limit: float | None = None) -> tuple[np.ndarray, float]:
    """Correlation function of the baseline-subtracted spectrum around one peak.

    `excess` is the stacked spectrum minus baseline (and minus neighbouring peaks). `limit` caps the
    half-width of the selected band so that it stops short of the nearest other mode. Returns
    (R at lags 0..NFFT/2 samples, band sample rate). The Welch estimate multiplies the true
    correlation by the window autocorrelation; that taper is divided out so damping is not inflated.
    """
    fs = BANDS[band]["fs"]
    df = f[1] - f[0]
    half = min(max(8 * zeta0 * f0, 8 * df), 0.45 * f0)
    if limit is not None:
        half = max(min(half, limit), 4 * df)
    u = (f - f0) / half
    taper = np.where(np.abs(u) < 0.8, 1.0, np.where(np.abs(u) < 1.0, 0.5 * (1 + np.cos(np.pi * (np.abs(u) - 0.8) / 0.2)), 0.0))
    r = np.fft.irfft(excess * taper, NFFT)[: NFFT // 2]
    return r / np.maximum(window_correlation()[: NFFT // 2], 0.2), fs


# --------------------------------------------------------------------------- EFDD
def efdd(f: np.ndarray, excess: np.ndarray, f0: float, zeta0: float, band: str,
         limit: float | None = None, hi: float = 0.9, lo: float = 0.3) -> ModeEstimate:
    """Enhanced FDD on the stacked trace: log decrement of the bell's correlation function."""
    r, fs = _band_correlation(f, excess, f0, zeta0, band, limit)
    if r[0] <= 0:
        return ModeEstimate(f0, np.nan, ok=False, method="efdd")
    r = r / r[0]
    up = 8
    sym = np.concatenate([r, r[:0:-1]])
    rr = signal.resample(sym, len(sym) * up)[: (len(r) - 1) * up]
    dt = 1.0 / (fs * up)
    ext = signal.argrelextrema(np.abs(rr), np.greater)[0]
    ext = ext[ext * dt < 0.45 * NFFT / fs]
    amp = np.abs(rr[ext])
    use = (amp <= hi) & (amp >= lo)
    if use.sum() < 3:
        use = amp >= min(lo, 0.5 * amp.max() if len(amp) else lo)
    if use.sum() < 3:
        return ModeEstimate(f0, np.nan, ok=False, method="efdd")
    first = int(np.argmax(use))
    stop = first + int(np.argmin(np.append(use[first:], False)))   # contiguous run only
    n, a = np.arange(first, stop), amp[first:stop]
    slope = np.polyfit(n, np.log(a), 1)[0]                          # per half cycle
    delta = -2 * slope
    zeta = delta / np.sqrt(delta**2 + 4 * np.pi**2)
    tt = ext[first:stop] * dt
    fd = 0.5 * (n[-1] - n[0]) / max(tt[-1] - tt[0], 1e-12)
    return ModeEstimate(float(fd / np.sqrt(max(1 - zeta**2, 1e-6))), float(zeta), ok=bool(zeta > 0), method="efdd")


# --------------------------------------------------------------------------- SSI-COV
def ssi_cov(f: np.ndarray, excess: np.ndarray, f0: float, zeta0: float, band: str,
            limit: float | None = None, orders: tuple[int, ...] = (2, 4, 6, 8)) -> ModeEstimate:
    """Covariance-driven stochastic subspace identification on the correlation of one peak band.

    Poles are computed for several model orders; the estimate is the median of the poles that stay
    within 2% of the candidate frequency (a one-line stabilisation diagram).
    """
    r, fs = _band_correlation(f, excess, f0, zeta0, band, limit)
    m = max(1, int(fs / (4.0 * f0)))
    r = r[::m]
    dt = m / fs
    usable = int(min(len(r), 0.45 * NFFT / m)) - 1
    i = min(60, usable // 2)
    if i < 6 or r[0] <= 0:
        return ModeEstimate(f0, np.nan, ok=False, method="ssi")
    idx = np.arange(i)[:, None] - np.arange(i)[None, :] + i
    Tm = r[idx]                                           # block Toeplitz, single channel
    U, s, _ = np.linalg.svd(Tm)
    fs_, zs_ = [], []
    for n in orders:
        O = U[:, :n] * np.sqrt(s[:n])
        A = np.linalg.lstsq(O[:-1], O[1:], rcond=None)[0]
        lam = np.log(np.linalg.eigvals(A).astype(complex)) / dt
        fr, zr = np.abs(lam) / (2 * np.pi), -lam.real / np.maximum(np.abs(lam), 1e-12)
        good = (np.abs(fr / f0 - 1) < 0.02) & (zr > 0) & (zr < 0.3) & (lam.imag > 0)
        if good.any():
            j = np.flatnonzero(good)[np.argmin(np.abs(fr[good] - f0))]
            fs_.append(fr[j])
            zs_.append(zr[j])
    if len(fs_) < 2:
        return ModeEstimate(f0, np.nan, ok=False, method="ssi")
    return ModeEstimate(float(np.median(fs_)), float(np.median(zs_)), method="ssi")


# --------------------------------------------------------------------------- random decrement
def random_decrement(x: np.ndarray, fs: float, f0: float, rel_band: float = 0.15,
                     n_cycles: int = 14, level: float = 1.0) -> ModeEstimate:
    """Random decrement signature of a band-passed time series, then log decrement of its envelope.

    Runs on raw device data. `level` is the trigger threshold in standard deviations.
    """
    sos = signal.butter(4, [f0 * (1 - rel_band), f0 * (1 + rel_band)], btype="band", fs=fs, output="sos")
    y = signal.sosfiltfilt(sos, x)
    thr = level * y.std()
    trig = np.flatnonzero((y[:-1] < thr) & (y[1:] >= thr))
    nseg = int(n_cycles * fs / f0)
    trig = trig[trig + nseg < len(y)]
    if len(trig) < 20:
        return ModeEstimate(f0, np.nan, ok=False, method="rdt")
    sig = np.zeros(nseg)
    for a in range(0, len(trig), 4096):
        sig += y[trig[a:a + 4096, None] + np.arange(nseg)[None, :]].sum(0)
    sig /= len(trig)
    env = np.abs(signal.hilbert(sig))
    per = fs / f0
    a, b = int(0.5 * per), int(min((n_cycles - 2) * per, nseg - per))
    sel = np.arange(a, b)
    sel = sel[env[sel] > 0.25 * env[a]]
    if len(sel) < 2 * per:
        return ModeEstimate(f0, np.nan, ok=False, method="rdt")
    slope = np.polyfit(sel / fs, np.log(env[sel]), 1)[0]
    zc = np.flatnonzero((sig[:-1] < 0) & (sig[1:] >= 0)).astype(float)
    zc += -sig[zc.astype(int)] / (sig[zc.astype(int) + 1] - sig[zc.astype(int)])
    fd = (len(zc) - 1) * fs / (zc[-1] - zc[0]) if len(zc) > 2 else f0
    wn = np.hypot(2 * np.pi * fd, slope)
    return ModeEstimate(float(wn / (2 * np.pi)), float(-slope / wn), ok=bool(slope < 0), method="rdt")


# --------------------------------------------------------------------------- FDD on sync frames
def fdd(X: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Frequency domain decomposition of simultaneous window spectra.

    X: (n_windows, n_f, n_phones, 3). Uses the two horizontal channels of every phone.
    Returns (s, u1, G): singular values (n_f, n_ch), first singular vectors (n_f, n_ch), CSD matrix.
    """
    k, nf, p, _ = X.shape
    h = X[:, :, :, :2].reshape(k, nf, 2 * p)
    G = np.einsum("kfa,kfb->fab", h, h.conj()) / k
    w, v = np.linalg.eigh(G)
    return w[:, ::-1].real, v[:, :, -1], G


def mode_shape(G: np.ndarray, f: np.ndarray, f0: float, zeta: float) -> np.ndarray:
    """First-mode amplitude at each phone from cross-phone blocks only (free of sensor-noise bias).

    Each pair of phones (p, q) shares a 2x2 block whose Frobenius norm is |phi_p * phi_q| * P. The
    blocks are averaged over the half-power band, then a rank-1 model is fitted to the off-diagonal
    products. Unknown yaw is irrelevant because the norm is rotation invariant. Needs 3+ phones;
    with 2 the result is the symmetric split (1, 1). Returned normalised to a maximum of 1.
    """
    nch = G.shape[1]
    p = nch // 2
    wgt = sdof_shape(f / f0, max(zeta, 0.004))
    sel = wgt > 0.5
    if not sel.any():
        sel = np.zeros(len(f), bool)
        sel[np.argmin(np.abs(f - f0))] = True
    Gm = (G[sel] * wgt[sel, None, None]).sum(0) / wgt[sel].sum()
    C = np.zeros((p, p))
    for a in range(p):
        for b in range(p):
            if a != b:
                C[a, b] = np.linalg.norm(Gm[2 * a:2 * a + 2, 2 * b:2 * b + 2])
    amp = np.sqrt(np.maximum(C.sum(1) / max(p - 1, 1), 1e-300))
    for _ in range(200):
        tot = (amp**2).sum()
        new = np.array([(C[a] @ amp) / max(tot - amp[a] ** 2, 1e-300) for a in range(p)])
        if np.allclose(new, amp, rtol=1e-9):
            break
        amp = new
    return amp / amp.max()
