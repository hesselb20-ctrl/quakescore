"""Building-level identification: stack, detect, estimate, bootstrap."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

import numpy as np
from scipy.stats import t as student_t

from ..features import BANDS, SessionFeatures
from .estimators import ModeEstimate, curve_fit, efdd, peak_model, ssi_cov
from .stack import Stack, baseline, build_stack, matched_filter, sdof_shape

COLOUR_SNR = 2.0     # fit the slope exponent only when the peak is this far above the baseline
MAX_PEAKS = 8
F_FLOOR = 0.0015     # relative model-error floor on frequency intervals (from high-SNR simulation)
ZETA_FLOOR = 0.10    # relative model-error floor on damping intervals


@dataclass
class Mode:
    f: float
    zeta: float
    band: str
    z: float                         # matched-filter detection score
    snr: float                       # peak-to-baseline power ratio in the stacked spectrum
    f_ci: tuple[float, float] = (np.nan, np.nan)      # 90% bootstrap interval
    zeta_ci: tuple[float, float] = (np.nan, np.nan)
    boot_ok: float = np.nan          # fraction of bootstrap replicates that re-found the peak
    n_sessions: int = 0
    n_contributors: int = 0
    features: dict = field(default_factory=dict)      # artefact-rejection features
    alt: dict = field(default_factory=dict)           # other estimators, for comparison
    label: str = "candidate"

    def to_dict(self) -> dict:
        return asdict(self)


def peak_features(stack: Stack, f0: float, zeta: float) -> dict:
    """Per-peak statistics used later by artefact rejection."""
    f = stack.f
    df = f[1] - f[0]
    h = max(5 * zeta * f0, 4 * df)
    a, b = max(int((f0 - h) / df), 1), min(int((f0 + h) / df) + 1, len(f))
    tmpl = sdof_shape(f[a:b] / f0, zeta)
    tz = tmpl - tmpl.mean()
    amps, sig, lvls = [], [], []
    for i in range(stack.n):
        tr = stack.traces[i]
        lvl = np.median(tr[max(a - 4 * (b - a), 1): b + 4 * (b - a)])
        r = tr[a:b] / lvl - 1.0
        amps.append(float((r * tz).sum() / (tz**2).sum()))
        sig.append(float(1.0 / np.sqrt(max(stack.k[i], 1) * (tz**2).sum())))
        lvls.append(float(lvl))
    amps, sig, lvls = np.array(amps), np.array(sig), np.array(lvls)
    # the same projection on the vertical channel: a lateral building mode has no vertical motion,
    # floor-borne machinery does
    wh = 1.0 / (sig * lvls) ** 2
    amp_h = float((wh * amps * lvls).sum() / wh.sum())
    vertical_ratio, vertical_z = 0.0, 0.0
    if stack.ztraces is not None:
        az, sz = [], []
        for i in range(stack.n):
            zt = stack.ztraces[i]
            lz = np.median(zt[max(a - 4 * (b - a), 1): b + 4 * (b - a)])
            az.append(float(((zt[a:b] / lz - 1.0) * tz).sum() / (tz**2).sum()) * lz)
            sz.append(lz / np.sqrt(max(stack.k[i], 1) * (tz**2).sum()))
        az, sz = np.array(az), np.array(sz)
        wz = 1.0 / sz**2
        amp_z = float((wz * az).sum() / wz.sum())
        vertical_z = amp_z * float(np.sqrt(wz.sum()))
        vertical_ratio = amp_z / amp_h if amp_h > 0 else 0.0
    zsess = amps / sig
    order = np.argsort(-amps)
    top = order[: max(1, int(np.ceil(0.2 * stack.n)))]
    pos = np.clip(amps, 0, None)
    core = sdof_shape(f / f0, max(zeta, 2 * df / f0)) > 0.5
    core[min(int(round(f0 / df)), len(f) - 1)] = True
    by_model: dict[str, list[float]] = {}
    by_contrib: dict[str, list[float]] = {}
    model_idx: dict[str, list[int]] = {}
    for i, sess in enumerate(stack.sessions):
        model_idx.setdefault(sess.phone_model, []).append(i)
    model_amp = {}
    for model, ii in model_idx.items():           # absolute peak power per phone model, inverse-variance mean
        wv = 1.0 / (sig[ii] * lvls[ii]) ** 2
        model_amp[model] = (float((wv * amps[ii] * lvls[ii]).sum() / wv.sum()), float(1.0 / np.sqrt(wv.sum())))
    floors, famp = [], []
    for i, s in enumerate(stack.sessions):
        by_model.setdefault(s.phone_model, []).append(zsess[i])
        by_contrib.setdefault(s.contributor, []).append(zsess[i])
        floors.append(s.floor)
        famp.append(amps[i] * np.median(stack.traces[i][a:b]))
    contrib_z = {c: float(np.sum(v) / np.sqrt(len(v))) for c, v in by_contrib.items()}
    return {
        "tone": float(np.median(stack.tone_mean()[core])),
        "frac_positive": float((zsess > 0).mean()),
        "concentration": float(pos[top].sum() / max(pos.sum(), 1e-300)),
        "top1_share": float(pos.max() / max(pos.sum(), 1e-300)),
        "support_z": float(amp_h * np.sqrt(wh.sum())),
        "vertical_ratio": float(vertical_ratio),
        "vertical_z": float(vertical_z),
        "n_models": len(by_model),
        "model_z": {m: float(np.sum(v) / np.sqrt(len(v))) for m, v in by_model.items()},
        "model_amp": model_amp,
        "model_sessions": {k: len(v) for k, v in model_idx.items()},
        "n_contrib_seen": int(sum(v > 2.0 for v in contrib_z.values())),
        "floor_corr": float(np.corrcoef(floors, famp)[0, 1]) if len(set(floors)) > 2 else float("nan"),
        "session_z_median": float(np.median(zsess)),
    }


def _fit_one(st: Stack, t: np.ndarray, base: np.ndarray, f0: float, zeta0: float,
             sub: np.ndarray) -> ModeEstimate:
    """Two-pass single-peak fit with everything else subtracted; the second pass re-centres the window."""
    df = st.f[1] - st.f[0]
    i = min(int(round(f0 / df)), len(t) - 1)
    colour = (t[i] - sub[i]) / base[i] - 1 > COLOUR_SNR
    est = curve_fit(st.f, t, [(f0, zeta0)], 0, base, sub, colour)[0]
    if est.ok:
        est = curve_fit(st.f, t, [(est.f, est.zeta)], 0, base, sub, colour)[0]
    return est


def _try_split(st: Stack, t: np.ndarray, base: np.ndarray, e: ModeEstimate, sub: np.ndarray,
               f_min: float = 10.0) -> list[ModeEstimate] | None:
    """Test whether a broad peak is really two close modes (typically the two horizontal directions).

    Fits one peak and two peaks over the same window and accepts the pair on an F-test of the
    deviance. Returns the two estimates or None.
    """
    win = (e.f * (1 - min(6 * e.zeta, 0.45)), e.f * (1 + min(6 * e.zeta, 0.45)))
    colour = e.snr > COLOUR_SNR
    one = curve_fit(st.f, t, [(e.f, e.zeta)], 0, base, sub, colour, win)[0]
    two = curve_fit(st.f, t, [(e.f * (1 - 0.7 * e.zeta), e.zeta / 3), (e.f * (1 + 0.7 * e.zeta), e.zeta / 3)],
                    0, base, sub, colour, win)
    if not (one.ok and all(x.ok for x in two)) or not np.isfinite(one.cost + two[0].cost):
        return None
    dof = two[0].nbins - 10
    if dof < 8:
        return None
    f_stat = ((one.cost - two[0].cost) / 4) / max(two[0].cost / dof, 1e-300)
    a, b = sorted(two, key=lambda x: x.f)
    sep = b.f / a.f - 1
    if f_stat < f_min or sep < 1.2 * max(a.zeta, b.zeta) or min(a.amp, b.amp) < 0.1 * max(a.amp, b.amp):
        return None
    return [a, b]


def _residual_z(st: Stack, t: np.ndarray, model: np.ndarray):
    """Matched-filter scores of the spectrum with known peaks removed."""
    resid = np.maximum(t - model, 0.05 * t)
    return matched_filter(st.f, resid, st.band)


def _too_close(f_new: float, z_new: float, found: list[ModeEstimate]) -> bool:
    return any(abs(f_new / e.f - 1) < max(0.015, 1.5 * e.zeta, 1.5 * z_new) for e in found)


def _backfit(st: Stack, t: np.ndarray, base: np.ndarray, found: list[ModeEstimate], sweeps: int,
             around: float | None = None) -> None:
    """Refit each peak in turn with all the others subtracted (optionally only those near `around`)."""
    f, zero = st.f, np.zeros_like(t)
    for _ in range(sweeps):
        for n in range(len(found)):
            if around is not None and abs(found[n].f / around - 1) > 0.35:
                continue
            others = sum((peak_model(f, o) for k, o in enumerate(found) if k != n), zero)
            e = _fit_one(st, t, base, found[n].f, found[n].zeta, others)
            if e.ok and e.snr > 0:
                found[n] = e


def find_peaks(st: Stack, z_min: float, idx: np.ndarray | None = None,
               shoulder: float = 0.15) -> list[tuple[ModeEstimate, float]]:
    """Iterative detect-fit-subtract in one band with backfitting. Returns (estimate, z) pairs.

    A candidate smaller than `shoulder` times the skirt of already-fitted peaks at its frequency, or
    inside the main lobe of a fitted peak, is treated as model mismatch and not as a new peak.
    """
    f = st.f
    df = f[1] - f[0]
    t = st.mean(idx)
    base = baseline(f, t)
    found: list[ModeEstimate] = []
    blocked: list[float] = []
    zero = np.zeros_like(t)
    for _ in range(MAX_PEAKS + 6):
        if len(found) >= MAX_PEAKS:
            break
        model = sum((peak_model(f, e) for e in found), zero)
        centres, z, zg = _residual_z(st, t, model)
        fc = f[centres]
        for e in found:
            z = np.where(np.abs(fc / e.f - 1) < max(0.015, 1.5 * e.zeta), -np.inf, z)
        for fb in blocked:
            z = np.where(np.abs(fc / fb - 1) < 0.02, -np.inf, z)
        i = int(np.argmax(z))
        if not np.isfinite(z[i]) or z[i] < z_min:
            break
        new = _fit_one(st, t, base, float(fc[i]), float(zg[i]), model)
        j = min(int(round(new.f / df)), len(t) - 1)
        if (not new.ok or abs(new.f / fc[i] - 1) > 0.05 or new.snr <= 0 or new.amp < shoulder * model[j]
                or _too_close(new.f, new.zeta, found)):
            blocked.append(float(fc[i]))
            continue
        pair = _try_split(st, t, base, new, model) if new.zeta > 0.035 else None
        found += pair if pair else [new]
        _backfit(st, t, base, found, 2, around=new.f)
    _backfit(st, t, base, found, 2)
    while True:                                          # prune peaks that did not survive backfitting
        scores = []
        for n, e in enumerate(found):
            others = sum((peak_model(f, o) for k, o in enumerate(found) if k != n), zero)
            centres, z, _ = _residual_z(st, t, others)
            j = int(np.argmin(np.abs(f[centres] - e.f)))
            zf = float(z[max(j - 2, 0): j + 3].max())
            jb = min(int(round(e.f / df)), len(t) - 1)
            rest = [o for k, o in enumerate(found) if k != n and o.amp > e.amp]
            bad = zf < z_min or e.amp < shoulder * others[jb] or _too_close(e.f, e.zeta, rest)
            scores.append((zf, bad))
        worst = [n for n, (zf, bad) in enumerate(scores) if bad]
        if not worst:
            return [(e, scores[n][0]) for n, e in enumerate(found)]
        found.pop(min(worst, key=lambda n: scores[n][0]))
        _backfit(st, t, base, found, 1)


def _interval(est: float, boot: list[float], n: int, floor: float) -> tuple[float, float]:
    """90% interval from bootstrap replicates, corrected for few sessions and for model error.

    A percentile bootstrap over n sessions is too narrow when n is small; the half-widths are
    scaled by sqrt(n/(n-1)) * t(n-1)/z. `floor` is a relative model-error term (the fitted shape is
    not exact), combined in quadrature, so that intervals do not shrink to nothing at high SNR.
    """
    lo, hi = np.percentile(boot, [5, 95])
    c = np.sqrt(n / (n - 1)) * student_t.ppf(0.95, n - 1) / 1.6449
    dl = np.hypot(c * max(est - lo, 0.0), floor * est)
    dh = np.hypot(c * max(hi - est, 0.0), floor * est)
    return float(est - dl), float(est + dh)


def identify(sessions: list[SessionFeatures], z_min: float = 6.0, n_boot: int = 100,
             rng: np.random.Generator | None = None, compare: bool = False,
             bands: tuple[str, ...] = ("L", "M", "H")) -> list[Mode]:
    """Identify all candidate modes of one building from its uploaded sessions."""
    rng = rng or np.random.default_rng(0)
    modes: list[Mode] = []
    for band in bands:
        st = build_stack(sessions, band)
        if st is None:
            continue
        peaks = find_peaks(st, z_min)
        if not peaks:
            continue
        f, t = st.f, st.mean()
        base = baseline(f, t)
        models = [peak_model(f, e) for e, _ in peaks]
        total = sum(models, np.zeros_like(t))
        n_contrib = len({s.contributor for s in st.sessions})
        band_modes = []
        for (e, zf), own in zip(peaks, models):
            m = Mode(e.f, e.zeta, band, zf, e.snr, n_sessions=st.n, n_contributors=n_contrib)
            m.features = peak_features(st, e.f, e.zeta)
            if compare:
                df = f[1] - f[0]
                i = min(int(round(e.f / df)), len(f) - 1)
                lo, hi = int(i * 0.97), int(i * 1.03) + 2
                m.alt["fdd_peak"] = {"f": float(f[lo + int(np.argmax(t[lo:hi]))]), "zeta": float("nan")}
                excess = t - base - (total - own)
                dist = min([abs(o.f - e.f) for o, _ in peaks if o is not e] or [np.inf])
                for name, fn in (("efdd", efdd), ("ssi", ssi_cov)):
                    r = fn(f, excess, e.f, e.zeta, band, 0.5 * dist)
                    m.alt[name] = {"f": r.f, "zeta": r.zeta, "ok": r.ok}
            band_modes.append((m, e, total - own))
        if n_boot > 0 and st.n >= 2:
            store = {id(m): ([], []) for m, _, _ in band_modes}
            for _ in range(n_boot):
                tb = st.mean(rng.integers(0, st.n, st.n))
                for m, e, sub in band_modes:
                    eb = curve_fit(f, tb, [(e.f, e.zeta)], 0, base, sub, e.snr > COLOUR_SNR)[0]
                    if eb.ok and eb.snr > 0.25 * e.snr and abs(eb.f / e.f - 1) < max(3 * e.zeta, 0.02) * 0.98:
                        store[id(m)][0].append(eb.f)
                        store[id(m)][1].append(eb.zeta)
            for m, _, _ in band_modes:
                fb, zb = store[id(m)]
                m.boot_ok = len(fb) / n_boot
                if len(fb) >= 10:
                    m.f_ci = _interval(m.f, fb, st.n, F_FLOOR)
                    m.zeta_ci = _interval(m.zeta, zb, st.n, ZETA_FLOOR)
        modes += [m for m, _, _ in band_modes]
    return _merge(modes)


def _merge(modes: list[Mode]) -> list[Mode]:
    """Where two bands report the same peak, keep the one whose home range contains it."""
    keep: list[Mode] = []
    for m in sorted(modes, key=lambda m: m.f):
        dup = next((k for k in keep if abs(k.f / m.f - 1) < 0.04 and k.band != m.band), None)
        if dup is None:
            keep.append(m)
            continue
        lo, hi = BANDS[m.band]["home"]
        if lo <= m.f < hi:
            keep[keep.index(dup)] = m
    return keep


def match_truth(modes: list[Mode], truth: list[dict], tol: float = 0.05) -> list[dict]:
    """Pair identified modes with simulator truth (nearest within tol). For evaluation only."""
    out = []
    for tm in truth:
        best = min(modes, key=lambda m: abs(m.f / tm["f"] - 1), default=None)
        if best is not None and abs(best.f / tm["f"] - 1) <= tol:
            out.append({"truth": tm, "mode": best, "f_err": best.f / tm["f"] - 1,
                        "zeta_err": best.zeta / tm["zeta"] - 1})
        else:
            out.append({"truth": tm, "mode": None, "f_err": np.nan, "zeta_err": np.nan})
    return out
