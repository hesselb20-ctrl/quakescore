"""Reference implementation of the on-device feature pipeline (DESIGN.md section 3.1).

Input: raw accelerometer samples with UTC-mapped timestamps. Output: SessionFeatures.
The Kotlin module android/dsp-core mirrors this file step for step.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from scipy import signal

from ..features import BANDS, HOP, NBINS, NFFT, BandFeatures, SessionFeatures


@dataclass(frozen=True)
class DeviceConfig:
    gate_rms_factor: float = 5.0        # a second is flagged above this multiple of the median RMS
    gate_tilt: float = 0.0035           # rad; flagged if gravity direction moves more than this
    flat_cos: float = 0.966             # cos(15 deg); session invalid if the phone is not flat
    sync_bands: tuple[str, ...] = ()    # bands for which per-window frames are kept (tier B)
    sync_ranges: tuple[tuple[float, float], ...] = ()   # frequency ranges kept in frames; empty = all


@lru_cache(maxsize=None)
def fir_taps(m: int) -> np.ndarray:
    """Decimation low-pass for factor m: pass 0.4, stop 0.5 of the output rate, about 80 dB.

    numtaps - 1 is a multiple of 2*m so that the anchored decimation phase is exact.
    """
    width = (0.5 - 0.4) / m                       # transition width as a fraction of the input rate
    numtaps, beta = signal.kaiserord(80.0, width / 0.5)
    numtaps += (-(numtaps - 1)) % (2 * m)
    return signal.firwin(numtaps, 0.45 / m, window=("kaiser", beta), fs=1.0)


def decimate_anchored(x: np.ndarray, i0: int, m: int) -> tuple[np.ndarray, int]:
    """Zero-phase FIR decimation by m. Output sample j sits at input absolute index j*m.

    x is (n, channels) with absolute index i0 for its first row. Returns (y, j0).
    """
    h = fir_taps(m)
    half = (len(h) - 1) // 2
    c0 = i0 + half
    c0 += (-c0) % m
    s = c0 - i0 - half
    n_out = (len(x) - s - 1 - 2 * half) // m + 1
    if n_out <= 0:
        return np.zeros((0, x.shape[1])), c0 // m
    y = signal.upfirdn(h, x[s:], down=m, axis=0)[2 * half // m: 2 * half // m + n_out]
    return y, c0 // m


def level_rotation(g: np.ndarray) -> np.ndarray:
    """Rows are the level-frame axes expressed in the device frame (z along measured gravity)."""
    z = g / np.linalg.norm(g)
    x = np.array([1.0, 0.0, 0.0]) - z[0] * z
    x /= np.linalg.norm(x)
    return np.stack([x, np.cross(z, x), z])


def _window_spectra(x: np.ndarray, starts: np.ndarray, fs: float) -> np.ndarray:
    """Scaled spectra (k, NBINS, 3): |X|^2 is the one-sided PSD of each window."""
    w = signal.get_window("hann", NFFT, fftbins=True)
    scale = np.sqrt(2.0 / (fs * (w**2).sum()))
    n = np.arange(NFFT) - (NFFT - 1) / 2
    out = np.empty((len(starts), NBINS, 3), np.complex64)
    for a in range(0, len(starts), 128):
        idx = starts[a:a + 128, None] + np.arange(NFFT)[None, :]
        seg = x[idx]                                             # (k, NFFT, 3)
        seg = seg - seg.mean(1, keepdims=True)
        slope = (seg * n[None, :, None]).sum(1, keepdims=True) / (n**2).sum()
        seg = seg - slope * n[None, :, None]
        out[a:a + 128] = np.fft.rfft(seg * w[None, :, None], axis=1) * scale
    return out


def process_session(ts: np.ndarray, acc: np.ndarray, meta: dict,
                    cfg: DeviceConfig = DeviceConfig()) -> SessionFeatures:
    """Run the whole on-device chain on one recording."""
    ts = np.asarray(ts, float)
    fs_raw = (len(ts) - 1) / (ts[-1] - ts[0])
    fs_g = 200.0 if fs_raw >= 190.0 else 100.0
    m1 = int(fs_g / 50.0)

    # 1. uniform epoch-anchored grid
    i0 = int(np.ceil(ts[0] * fs_g))
    i1 = int(np.floor(ts[-1] * fs_g))
    tg = np.arange(i0, i1 + 1) / fs_g
    xg = np.stack([np.interp(tg, ts, acc[:, a]) for a in range(3)], 1)

    # 2. privacy low-pass and decimation to 50 Hz
    x50, j50 = decimate_anchored(xg, i0, m1)
    del xg

    # 3. per-second gate
    nsec = len(x50) // 50
    blocks = x50[: nsec * 50].reshape(nsec, 50, 3)
    bmean = blocks.mean(1)
    brms = np.sqrt(((blocks - bmean[:, None, :]) ** 2).mean((1, 2)))
    g_med = np.median(bmean, 0)
    g_unit = g_med / np.linalg.norm(g_med)
    cosang = (bmean @ g_unit) / np.maximum(np.linalg.norm(bmean, axis=1), 1e-9)
    tilt = np.arccos(np.clip(cosang, -1, 1))
    flagged = (brms > cfg.gate_rms_factor * np.median(brms)) | (tilt > cfg.gate_tilt)
    flat = abs(g_unit[2]) >= cfg.flat_cos

    # 4. levelling
    good = ~flagged
    g_vec = bmean[good].mean(0) if good.any() else g_med
    xh = x50 @ level_rotation(g_vec).T

    # 5. zoom bands
    xm, jm = decimate_anchored(xh, j50, 4)
    xl, jl = decimate_anchored(xm, jm, 4)
    data = {"H": (xh, j50), "M": (xm, jm), "L": (xl, jl)}
    sec_t0 = j50 / 50.0
    flag_cum = np.concatenate([[0], np.cumsum(flagged)])

    bands: dict[str, BandFeatures] = {}
    n_total = n_acc = 0
    for name, (x, j0) in data.items():
        fs = BANDS[name]["fs"]
        k0 = -(-j0 // HOP)
        k1 = (j0 + len(x) - NFFT) // HOP
        ks = np.arange(k0, k1 + 1) if k1 >= k0 else np.zeros(0, int)
        t_lo = ks * HOP / fs
        s_lo = np.clip(np.floor(t_lo - sec_t0).astype(int), 0, nsec)
        s_hi = np.clip(np.ceil(t_lo + NFFT / fs - sec_t0).astype(int), 0, nsec)
        inside = (t_lo >= sec_t0) & (t_lo + NFFT / fs <= sec_t0 + nsec)
        ok = inside & ((flag_cum[s_hi] - flag_cum[s_lo]) == 0) & flat
        n_total += len(ks)
        n_acc += int(ok.sum())
        ks = ks[ok]
        if len(ks) == 0:
            bands[name] = BandFeatures(0, np.zeros((NBINS, 3, 3), np.complex64), np.zeros((NBINS, 3), np.float32))
            continue
        X = _window_spectra(x, ks * HOP - j0, fs)
        csd = np.einsum("kfa,kfb->fab", X, X.conj()) / len(ks)
        p4 = (np.abs(X) ** 4).mean(0)
        bf = BandFeatures(len(ks), csd.astype(np.complex64), p4.astype(np.float32))
        if name in cfg.sync_bands:
            f = np.arange(NBINS) * fs / NFFT
            sel = np.zeros(NBINS, bool)
            for lo, hi in (cfg.sync_ranges or ((0.0, 1e9),)):
                sel |= (f >= lo) & (f <= hi)
            bf.win_idx, bf.frame_bins, bf.frames = ks, np.flatnonzero(sel), X[:, sel, :]
        bands[name] = bf

    return SessionFeatures(
        session_id=meta.get("session_id", "s"), building_id=meta.get("building_id", "b"),
        contributor=meta.get("contributor", "c0"), phone_model=meta.get("phone_model", "unknown"),
        floor=int(meta.get("floor", 0)), floor_method=meta.get("floor_method", "manual"),
        t_start=float(60 * round(ts[0] / 60)), duration=float(ts[-1] - ts[0]), fs_raw=float(fs_raw),
        lsb=float(meta.get("lsb", 0.0)), sync_source=meta.get("sync_source", "ntp"),
        sync_sigma_ms=float(meta.get("sync_sigma_ms", 0.0)),
        accept_fraction=n_acc / max(n_total, 1), bands=bands, temp_c=meta.get("temp_c"),
        provenance=meta.get("provenance", "SIM"), truth=meta.get("truth"))
