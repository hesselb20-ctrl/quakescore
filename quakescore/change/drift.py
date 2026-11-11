"""Frequency tracking: environmental correction and detection of a lasting change.

A building's frequency wanders by a fraction of a percent to a few percent with temperature, season,
moisture and vibration amplitude (docs/references.md). A stiffness loss shows up as a lasting drop
on top of that. The detector fits the environmental terms and a step at every admissible date
together, so a real step is not absorbed into the seasonal terms, and takes the most significant
step. The threshold is set for a chosen false-alarm rate on change-free series.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class ChangeResult:
    alarm: bool
    t_stat: float            # most extreme step statistic over all admissible change dates
    step: float              # relative frequency step at that date (negative = softening)
    onset: float             # day of the detected step
    temp_coeff: float        # relative frequency change per degree C
    resid_sigma: float       # relative residual scatter after correction
    trend_per_year: float    # relative linear trend per year (fitted without a step)


def _design(t: np.ndarray, temp: np.ndarray | None, amp: np.ndarray | None, seasonal: bool) -> np.ndarray:
    n = len(t)                       # regressors are added only when the series can support them
    cols = [np.ones_like(t)]
    if temp is not None and n >= 8:
        cols.append(temp - temp.mean())
    if amp is not None and n >= 16:
        cols.append(amp - amp.mean())
    if seasonal and n >= 24 and (t.max() - t.min()) > 240:
        cols += [np.sin(2 * np.pi * t / 365.25), np.cos(2 * np.pi * t / 365.25)]
    return np.stack(cols, 1)


def detect_change(t_days: np.ndarray, f: np.ndarray, temp: np.ndarray | None = None,
                  amp: np.ndarray | None = None, threshold: float = 4.5, min_seg: int = 3,
                  seasonal: bool = True) -> ChangeResult:
    """Step detection in a frequency series with environmental regressors.

    t_days: epoch times; f: frequency estimates; temp: outdoor temperature per epoch (optional);
    amp: log vibration amplitude per epoch (optional). Works on log-frequency, so steps are relative.
    """
    t = np.asarray(t_days, float)
    y = np.log(np.asarray(f, float))
    n = len(y)
    X0 = _design(t, temp, amp, seasonal)
    best = (0.0, 0.0, t[0])
    if n >= X0.shape[1] + 2 * min_seg:
        for i in range(min_seg, n - min_seg + 1):
            X = np.column_stack([X0, (np.arange(n) >= i).astype(float)])
            beta, res, rank, _ = np.linalg.lstsq(X, y, rcond=None)
            dof = n - X.shape[1]
            if rank < X.shape[1] or dof < 1:
                continue
            r = y - X @ beta
            s2 = (r @ r) / dof
            cov = s2 * np.linalg.inv(X.T @ X)
            ts = beta[-1] / np.sqrt(max(cov[-1, -1], 1e-300))
            if abs(ts) > abs(best[0]):
                best = (float(ts), float(beta[-1]), float(t[i]))
    Xt = np.column_stack([X0, (t - t.mean()) / 365.25])
    beta, *_ = np.linalg.lstsq(Xt, y, rcond=None)
    resid = y - Xt @ beta
    tc = float(beta[1]) if temp is not None and n >= 8 else 0.0
    return ChangeResult(alarm=abs(best[0]) > threshold, t_stat=best[0], step=float(np.expm1(best[1])),
                        onset=best[2], temp_coeff=tc, resid_sigma=float(resid.std(ddof=min(Xt.shape[1], n - 1))),
                        trend_per_year=float(beta[-1]))
