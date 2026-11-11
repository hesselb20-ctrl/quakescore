"""Export the dsp-core constants and test vectors from the Python reference pipeline.

Run from the repository root:

    PYTHONPATH=. .venv/Scripts/python.exe experiments/export_device_vectors.py

Writes
    android/dsp-core/src/main/kotlin/org/quakescore/dsp/FirTaps.kt   generated FIR taps (repr, bit-identical)
    tests/vectors/fir_taps.json          the same taps as JSON
    tests/vectors/decimate_case.json     one decimate_anchored case (random input, odd start index)
    tests/vectors/stream_a.csv.gz        ~10 min at ~198.4 Hz, 200 Hz grid, transient burst (RMS gate)
    tests/vectors/stream_a_expected.json
    tests/vectors/stream_b.csv.gz        ~25 min at ~99.6 Hz, 100 Hz grid, tilt step that ends the session
    tests/vectors/stream_b_expected.json
    tests/vectors/stream_c.csv.gz        20 min at ~59.94 Hz (browser DeviceMotion rate), 100 Hz grid
                                         (upsampled), 2 ms absolute timestamp jitter, transient burst
    tests/vectors/stream_c_expected.json
    web/collector/fir_taps.js            the FIR taps for the browser port (repr, bit-identical)

Stream CSV format (one sample per line, no header):
    dt_ns,cx,cy,cz
dt_ns is the sensor-timestamp increment in integer nanoseconds from the previous sample (0 for the
first); cx, cy, cz are integer sensor counts. The consumer rebuilds
    t_i   = t0 + (cumsum(dt_ns)_i as double) * 1e-9          (UTC seconds)
    acc_i = counts_i (as double) * lsb                         (m/s^2)
with t0 and lsb taken from the matching *_expected.json, exactly as this script does.

The expected outputs come from process_session_streaming below. It is the reference pipeline
(quakescore/device/pipeline.py) with the session-wide statistics replaced by the streaming rules that
android/dsp-core implements (warm-up gravity and gate thresholds, frozen; flagged-run session end;
rate decision from a 10 s probe). It reuses the pipeline building blocks unchanged.
"""
from __future__ import annotations

import base64
import gzip
import json
import math
from pathlib import Path

import numpy as np

from quakescore.device.pipeline import (DeviceConfig, _window_spectra, decimate_anchored, fir_taps,
                                        level_rotation)
from quakescore.features import BANDS, HOP, NBINS, NFFT

ROOT = Path(__file__).resolve().parents[1]
VEC = ROOT / "tests" / "vectors"
KT = ROOT / "android" / "dsp-core" / "src" / "main" / "kotlin" / "org" / "quakescore" / "dsp" / "FirTaps.kt"
JS_TAPS = ROOT / "web" / "collector" / "fir_taps.js"

WARMUP_S = 120          # seconds of 50 Hz data that define gravity, levelling and the RMS median
RATE_PROBE_S = 10.0     # raw-sample span used to choose the 200 Hz or 100 Hz grid
MAX_FLAGGED_RUN = 60    # more consecutive flagged seconds than this ends the session


# ----------------------------------------------------------------------------- streaming reference

def pack_band(csd: np.ndarray, p4: np.ndarray) -> tuple[str, str]:
    """Upload packing: csd (NBINS,3,3) and p4 (NBINS,3) as base64 little-endian float32."""
    c = np.empty((NBINS, 9), "<f4")
    c[:, 0] = csd[:, 0, 0].real
    c[:, 1] = csd[:, 1, 1].real
    c[:, 2] = csd[:, 2, 2].real
    c[:, 3], c[:, 4] = csd[:, 0, 1].real, csd[:, 0, 1].imag
    c[:, 5], c[:, 6] = csd[:, 0, 2].real, csd[:, 0, 2].imag
    c[:, 7], c[:, 8] = csd[:, 1, 2].real, csd[:, 1, 2].imag
    p = np.ascontiguousarray(p4, "<f4")
    return base64.b64encode(c.tobytes()).decode(), base64.b64encode(p.tobytes()).decode()


def _empty_band() -> dict:
    csd, p4 = pack_band(np.zeros((NBINS, 3, 3), np.complex64), np.zeros((NBINS, 3), np.float32))
    return {"k": 0, "n_total": 0, "windows": [], "csd": csd, "p4": p4}


def process_session_streaming(ts: np.ndarray, acc: np.ndarray, cfg: DeviceConfig = DeviceConfig(),
                              warmup_s: int = WARMUP_S, probe_s: float = RATE_PROBE_S,
                              max_run: int = MAX_FLAGGED_RUN) -> dict:
    """Streaming-equivalent of pipeline.process_session (see android/dsp-core SessionProcessor.kt)."""
    ts = np.asarray(ts, float)
    acc = np.asarray(acc, float)
    n = len(ts)
    out: dict = {"fs_raw": (n - 1) / (ts[-1] - ts[0]), "duration": float(ts[-1] - ts[0]),
                 "t_start": float(60 * round(ts[0] / 60))}

    # 0. grid rate from a probe at the start of the stream (the reference uses the whole session)
    hit = np.flatnonzero(ts - ts[0] >= probe_s)
    nd = int(hit[0]) if len(hit) else n - 1
    fs_probe = nd / (ts[nd] - ts[0])
    fs_g = 200.0 if fs_probe >= 190.0 else 100.0
    m1 = int(fs_g / 50.0)
    out.update(fs_probe=fs_probe, fs_g=fs_g)

    # 1-2. identical to the reference
    i0 = int(np.ceil(ts[0] * fs_g))
    i1 = int(np.floor(ts[-1] * fs_g))
    tg = np.arange(i0, i1 + 1) / fs_g
    xg = np.stack([np.interp(tg, ts, acc[:, a]) for a in range(3)], 1)
    x50, j50 = decimate_anchored(xg, i0, m1)
    del xg
    out.update(i0=i0, j50=int(j50), n50=len(x50))

    # 3. per-second statistics; thresholds and gravity from the warm-up only, then frozen
    nsec = len(x50) // 50
    if nsec < warmup_s:
        out.update(status="too_short", nsec=nsec, flagged=[], end_second=None, accept_fraction=0.0,
                   bands={b: _empty_band() for b in BANDS})
        return out
    blocks = x50[: nsec * 50].reshape(nsec, 50, 3)
    bmean = blocks.mean(1)
    brms = np.sqrt(((blocks - bmean[:, None, :]) ** 2).mean((1, 2)))
    g_med = np.median(bmean[:warmup_s], 0)
    g_unit = g_med / np.linalg.norm(g_med)
    rms_med = float(np.median(brms[:warmup_s]))
    cosang = (bmean @ g_unit) / np.maximum(np.linalg.norm(bmean, axis=1), 1e-9)
    tilt = np.arccos(np.clip(cosang, -1, 1))
    flagged = (brms > cfg.gate_rms_factor * rms_med) | (tilt > cfg.gate_tilt)
    flat = bool(abs(g_unit[2]) >= cfg.flat_cos)
    good_w = ~flagged[:warmup_s]
    g_vec = bmean[:warmup_s][good_w].mean(0) if good_w.any() else g_med
    out.update(g_med=g_med.tolist(), rms_med=rms_med, g_vec=g_vec.tolist(), flat=flat)
    if not flat:
        out.update(status="not_flat", nsec=warmup_s, flagged=[], end_second=None, accept_fraction=0.0,
                   bands={b: _empty_band() for b in BANDS})
        return out

    # (d) a run of more than max_run flagged seconds ends the session at the end of that second
    run, end_sec = 0, None
    for s in range(nsec):
        run = run + 1 if flagged[s] else 0
        if run > max_run:
            end_sec = s
            break
    if end_sec is not None:
        nsec = end_sec + 1
        x50 = x50[: 50 * nsec]
        flagged = flagged[:nsec]
        out["n50"] = len(x50)
    out.update(status="ended_flagged_run" if end_sec is not None else "complete", nsec=nsec,
               flagged=np.flatnonzero(flagged).tolist(), end_second=end_sec)

    # 4-5. levelling and zoom bands, as in the reference
    xh = x50 @ level_rotation(g_vec).T
    xm, jm = decimate_anchored(xh, j50, 4)
    xl, jl = decimate_anchored(xm, jm, 4)
    data = {"H": (xh, j50), "M": (xm, jm), "L": (xl, jl)}
    sec_t0 = j50 / 50.0
    flag_cum = np.concatenate([[0], np.cumsum(flagged)])

    bands = {}
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
        nt = len(ks)
        ks = ks[ok]
        if len(ks) == 0:
            bands[name] = _empty_band() | {"n_total": nt, "j0": int(j0), "n": len(x)}
            continue
        X = _window_spectra(x, ks * HOP - j0, fs)
        csd = (np.einsum("kfa,kfb->fab", X, X.conj()) / len(ks)).astype(np.complex64)
        p4 = (np.abs(X) ** 4).mean(0).astype(np.float32)
        c64, p64 = pack_band(csd, p4)
        bands[name] = {"k": len(ks), "n_total": nt, "windows": ks.tolist(), "j0": int(j0), "n": len(x),
                       "csd": c64, "p4": p64}
    out.update(accept_fraction=n_acc / max(n_total, 1), bands=bands)
    return out


# ----------------------------------------------------------------------------- synthetic streams

def synth_stream(seed: int, t0: float, fs_raw: float, dur: float, lsb: float, tones, tilt_deg,
                 noise: float, burst=None, tilt_step=None, abs_jitter_ns=None):
    """Sensor-like stream: gravity with tilt, sinusoids, Gaussian noise, jittered ns timestamps, counts.

    By default each timestamp increment has 20 us of jitter (sensor clock). With abs_jitter_ns the
    jitter is applied to the absolute times instead (browser event timestamps: coarse, but not a random
    walk), and the times are then forced to be strictly increasing by at least 1 ns.
    """
    rng = np.random.default_rng(seed)
    n = int(dur * fs_raw)
    period_ns = 1e9 / fs_raw
    if abs_jitter_ns is None:
        dt = np.round(period_ns + rng.normal(0.0, 20e3, n)).astype(np.int64)   # 20 us timestamp jitter
        dt[0] = 0
    else:
        idx = np.arange(n, dtype=np.int64)
        tj = np.round(idx * period_ns + rng.normal(0.0, abs_jitter_ns, n)).astype(np.int64)
        tj = np.maximum.accumulate(tj - idx) + idx           # strictly increasing
        dt = np.diff(tj, prepend=tj[0])
        dt[0] = 0
    off = np.cumsum(dt)
    ts = t0 + off * 1e-9
    t = ts - ts[0]
    ax, ay = np.radians(tilt_deg)
    g = 9.80665 * np.array([np.sin(ay), -np.sin(ax) * np.cos(ay), np.cos(ax) * np.cos(ay)])
    acc = np.tile(g, (n, 1)) + rng.normal(0.0, noise, (n, 3))
    for f, amp, axis in tones:
        acc[:, axis] += amp * np.sin(2 * np.pi * f * t + rng.uniform(0, 2 * np.pi))
    if burst is not None:
        b0, b1, s = burst
        sel = (ts >= b0) & (ts < b1)
        acc[sel] += rng.normal(0.0, s, (int(sel.sum()), 3))
    if tilt_step is not None:
        ts_step, rad = tilt_step
        sel = ts >= ts_step                      # small rotation about the device x axis
        c, s_ = np.cos(rad), np.sin(rad)
        y, z = acc[sel, 1].copy(), acc[sel, 2].copy()
        acc[sel, 1], acc[sel, 2] = c * y - s_ * z, s_ * y + c * z
    counts = np.round(acc / lsb).astype(np.int64)
    return dt, counts


def write_stream(name: str, dt, counts, meta: dict):
    t0, lsb = meta["t0"], meta["lsb"]
    with gzip.open(VEC / f"{name}.csv.gz", "wt", newline="\n", compresslevel=9) as f:
        for d, (cx, cy, cz) in zip(dt.tolist(), counts.tolist()):
            f.write(f"{d},{cx},{cy},{cz}\n")
    off = np.cumsum(dt)
    ts = t0 + off.astype(float) * 1e-9
    acc = counts.astype(float) * lsb
    res = process_session_streaming(ts, acc)
    res = {"meta": meta, "n_samples": len(ts), **res}
    (VEC / f"{name}_expected.json").write_text(json.dumps(res, indent=1) + "\n")
    b = res["bands"]
    print(f"{name}: n={len(ts)} fs_raw={res['fs_raw']:.4f} fs_g={res['fs_g']} status={res['status']} "
          f"nsec={res['nsec']} flagged={len(res['flagged'])} end={res['end_second']} "
          f"k(L,M,H)=({b['L']['k']},{b['M']['k']},{b['H']['k']}) "
          f"n_total=({b['L']['n_total']},{b['M']['n_total']},{b['H']['n_total']}) "
          f"accept={res['accept_fraction']:.3f}")


# ----------------------------------------------------------------------------- outputs

def write_fir():
    lines = ["// GENERATED by experiments/export_device_vectors.py from quakescore.device.pipeline.fir_taps.",
             "// Do not edit by hand. Values are Python repr() of float64, so they parse to identical doubles.",
             "package org.quakescore.dsp", "", "object FirTaps {"]
    for m in (4, 2):
        h = fir_taps(m)
        lines.append(f"    /** Decimation by {m}: {len(h)} taps, linear phase, centre tap index {(len(h) - 1) // 2}. */")
        lines.append(f"    val M{m}: DoubleArray = doubleArrayOf(")
        vals = [repr(float(v)) for v in h]
        for i in range(0, len(vals), 4):
            lines.append("        " + ", ".join(vals[i:i + 4]) + ",")
        lines.append("    )")
        lines.append("")
    lines += ["    fun forFactor(m: Int): DoubleArray = when (m) {", "        4 -> M4", "        2 -> M2",
              "        else -> throw IllegalArgumentException(\"no taps for factor $m\")", "    }", "}", ""]
    KT.parent.mkdir(parents=True, exist_ok=True)
    KT.write_text("\n".join(lines), newline="\n")
    (VEC / "fir_taps.json").write_text(json.dumps({str(m): [float(v) for v in fir_taps(m)] for m in (2, 4)}) + "\n")


def write_fir_js():
    """The same taps for web/collector/dsp.js (repr, so JavaScript parses them to identical doubles)."""
    lines = ["// GENERATED by experiments/export_device_vectors.py from quakescore.device.pipeline.fir_taps.",
             "// Do not edit by hand. Values are Python repr() of float64, so they parse to identical doubles.",
             ""]
    for m in (4, 2):
        h = fir_taps(m)
        lines.append(f"/** Decimation by {m}: {len(h)} taps, linear phase, centre tap index {(len(h) - 1) // 2}. */")
        lines.append(f"export const TAPS{m} = new Float64Array([")
        vals = [repr(float(v)) for v in h]
        for i in range(0, len(vals), 4):
            lines.append("  " + ", ".join(vals[i:i + 4]) + ",")
        lines.append("]);")
        lines.append("")
    JS_TAPS.parent.mkdir(parents=True, exist_ok=True)
    JS_TAPS.write_text("\n".join(lines), newline="\n")


def write_decimate_case():
    rng = np.random.default_rng(11)
    x = rng.normal(0.0, 1.0, (1500, 3)) + np.array([0.1, -0.2, 9.8])
    cases = []
    for m, i0 in ((4, 1_234_567_891), (2, 987_654_321)):
        y, j0 = decimate_anchored(x, i0, m)
        cases.append({"m": m, "i0": i0, "j0": int(j0), "y": y.tolist()})
    (VEC / "decimate_case.json").write_text(json.dumps({"x": x.tolist(), "cases": cases}) + "\n")


def second_origin(t0: float, fs_g: float) -> float:
    """UTC time of the first gate second (j50 / 50) for a stream starting at t0."""
    m = int(fs_g / 50.0)
    half = (len(fir_taps(m)) - 1) // 2
    c0 = int(np.ceil(t0 * fs_g)) + half
    c0 += (-c0) % m
    return (c0 // m) / 50.0


def main():
    VEC.mkdir(parents=True, exist_ok=True)
    write_fir()
    write_decimate_case()
    # Disturbances start half-way through a gate second so that no second sits near a threshold.
    t0a = 1_793_000_000.371
    sa = second_origin(t0a, 200.0)
    meta_a = {"t0": t0a, "lsb": 0.0012, "fs_nominal": 198.4}
    dt, c = synth_stream(1, t0a, 198.4, 600.0, 0.0012, [(1.3, 2e-3, 0), (7.9, 1e-3, 1), (3.1, 6e-4, 2)],
                         (3.0, 2.0), 3e-3, burst=(sa + 300.5, sa + 302.5, 0.05))
    write_stream("stream_a", dt, c, meta_a)
    t0b = 1_793_086_400.913
    sb = second_origin(t0b, 100.0)
    meta_b = {"t0": t0b, "lsb": 0.0012, "fs_nominal": 99.6}
    dt, c = synth_stream(2, t0b, 99.6, 1500.0, 0.0012, [(0.27, 3e-3, 0), (2.2, 1e-3, 1), (11.0, 8e-4, 0)],
                         (-2.0, 4.0), 3e-3, tilt_step=(sb + 1390.5, 0.01))
    write_stream("stream_b", dt, c, meta_b)
    # Browser-like: DeviceMotion at ~59.94 Hz (upsampled onto the 100 Hz grid), coarse event times.
    # The burst sits after the warm-up and before the single band-L window (gate seconds ~293-949).
    t0c = 1_793_172_800.557
    sc = second_origin(t0c, 100.0)
    meta_c = {"t0": t0c, "lsb": 0.0012, "fs_nominal": 59.94}
    dt, c = synth_stream(3, t0c, 59.94, 1200.0, 0.0012, [(1.3, 2e-3, 0), (7.0, 1e-3, 1)], (2.5, -3.0), 3e-3,
                         burst=(sc + 200.5, sc + 202.5, 0.05), abs_jitter_ns=2e6)
    write_stream("stream_c", dt, c, meta_c)
    write_fir_js()


if __name__ == "__main__":
    main()
