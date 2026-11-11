"""Session feature container: exactly what a phone uploads, nothing more."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

NFFT = 2048
HOP = NFFT // 2
NBINS = NFFT // 2 + 1

# rate (Hz), search range for peak centres (Hz), home range used when two bands see the same peak
BANDS = {
    "L": {"fs": 3.125, "search": (0.08, 1.20), "home": (0.0, 1.0)},
    "M": {"fs": 12.5, "search": (0.60, 4.70), "home": (1.0, 4.0)},
    "H": {"fs": 50.0, "search": (2.50, 18.0), "home": (4.0, 25.0)},
}


def band_freqs(band: str) -> np.ndarray:
    return np.arange(NBINS) * BANDS[band]["fs"] / NFFT


@dataclass
class BandFeatures:
    k: int                              # accepted windows
    csd: np.ndarray                     # (NBINS, 3, 3) complex64, mean one-sided CSD, (m/s^2)^2/Hz
    p4: np.ndarray                      # (NBINS, 3) float32, mean squared per-window PSD
    win_idx: np.ndarray | None = None   # (k,) absolute window indices (tier B)
    frames: np.ndarray | None = None    # (k, n_sel, 3) complex64 scaled window spectra (tier B)
    frame_bins: np.ndarray | None = None  # (n_sel,) bin indices covered by frames


@dataclass
class SessionFeatures:
    session_id: str
    building_id: str
    contributor: str
    phone_model: str
    floor: int
    floor_method: str
    t_start: float                      # UTC seconds, rounded to the minute on upload
    duration: float
    fs_raw: float
    lsb: float
    sync_source: str
    sync_sigma_ms: float
    accept_fraction: float
    bands: dict[str, BandFeatures] = field(default_factory=dict)
    temp_c: float | None = None
    provenance: str = "SIM"
    truth: dict | None = None           # simulator ground truth; never present on real uploads

    def trace(self, band: str) -> np.ndarray:
        """Horizontal trace G_xx + G_yy (rotation invariant), corrected for interpolation droop."""
        c = self.bands[band].csd
        t = c[:, 0, 0].real + c[:, 1, 1].real
        return t / droop(band_freqs(band), self.fs_raw)

    def tone_stat(self, band: str) -> np.ndarray:
        """Normalised periodogram variance per bin, horizontal axes pooled. Gaussian: 1, tone: 0."""
        b = self.bands[band]
        p = np.stack([b.csd[:, 0, 0].real, b.csd[:, 1, 1].real], 1)
        cv2 = b.p4[:, :2] / np.maximum(p, 1e-300) ** 2 - 1.0
        w = p / np.maximum(p.sum(1, keepdims=True), 1e-300)
        return (cv2 * w).sum(1)


def droop(f: np.ndarray, fs_raw: float) -> np.ndarray:
    """Power response of linear interpolation from the raw rate: sinc^4(f / fs_raw)."""
    return np.sinc(np.asarray(f) / fs_raw) ** 4
