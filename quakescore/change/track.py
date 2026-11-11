"""Track a building's frequency over time by registering each epoch against reference modes.

Detecting peaks afresh in every epoch is fragile: when the fundamental is missed, the next mode up
(often the other horizontal direction, 10-30% higher) is taken for it and the series jumps. Here the
reference modes are identified once from a baseline period, and each later epoch is described by one
number: the common relative shift that best aligns all reference peaks with the epoch's stacked
spectrum. Stiffness loss moves all modes by the same factor, so every peak contributes, no per-epoch
detection threshold is needed, and a single peak cannot be mistaken for its neighbour.
"""
from __future__ import annotations

import numpy as np

from ..features import SessionFeatures
from ..ident.stack import build_stack, sdof_shape, whiten


def epoch_shift(sessions: list[SessionFeatures], band: str, ref: list[tuple[float, float]],
                lo: float = -0.16, hi: float = 0.06, step: float = 0.001) -> tuple[float, float]:
    """Relative frequency shift of an epoch against reference modes [(f, zeta), ...], and its z-score.

    Scans a common shift, scoring a zero-mean matched filter summed over all reference peaks on the
    whitened stacked spectrum. Returns (shift, z); z below about 4 means the epoch carries no usable
    signal.
    """
    st = build_stack(sessions, band)
    if st is None or not ref:
        return 0.0, 0.0
    f = st.f
    r, _, sigma = whiten(f, st.mean(), band)
    df = f[1] - f[0]
    fmax = 0.8 * f[-1]
    deltas = np.arange(lo, hi + step / 2, step)
    score = np.zeros(len(deltas))
    for i, d in enumerate(deltas):
        num = norm = 0.0
        for f0, zeta in ref:
            fc = f0 * (1 + d)
            h = max(5 * zeta * fc, 4 * df)
            a, b = max(int((fc - h) / df), 1), min(int((fc + h) / df) + 1, int(fmax / df))
            if b - a < 4:
                continue
            tm = sdof_shape(f[a:b] / fc, zeta)
            tm = tm - tm.mean()
            num += float(r[a:b] @ tm)
            norm += float(tm @ tm)
        score[i] = num / (sigma * np.sqrt(norm)) if norm > 0 else 0.0
    k = int(np.argmax(score))
    d = deltas[k]
    if 0 < k < len(deltas) - 1:                      # parabolic refinement of the maximum
        y0, y1, y2 = score[k - 1], score[k], score[k + 1]
        den = y0 - 2 * y1 + y2
        if den < 0:
            d += 0.5 * (y0 - y2) / den * step
    return float(d), float(score[k])
