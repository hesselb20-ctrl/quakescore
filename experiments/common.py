"""Shared helpers for experiment scripts."""
from __future__ import annotations

import json
import os
import pathlib
import pickle
import time
import zlib
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures.process import BrokenProcessPool

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
WORKERS = int(os.environ.get("QS_WORKERS", "6"))
UG = 9.80665e-6


def seed_of(*args) -> int:
    """Deterministic seed from arbitrary arguments (Python's hash() is salted per process)."""
    return zlib.crc32(repr(args).encode())


def home_band(f: float) -> str:
    return "L" if f < 1.0 else ("M" if f < 4.0 else "H")


def bands_for(freqs) -> tuple[str, ...]:
    return tuple(sorted({home_band(f) for f in freqs}, key="LMH".index))


def run_pool(fn, tasks: list, workers: int = WORKERS, label: str = "", checkpoint: str | None = None,
             chunk: int | None = None) -> list:
    """Map fn over tasks in worker processes, in chunks.

    A worker killed from outside (shared machine) breaks the pool; the chunk is then retried with a
    fresh pool. With `checkpoint`, finished chunks are saved under results/cache and a rerun resumes.
    Delete the checkpoint file when the code under test changes.
    """
    t0 = time.time()
    ck = (RESULTS / "cache" / f"{checkpoint}.pkl") if checkpoint else None
    done: dict[int, object] = pickle.loads(ck.read_bytes()) if ck and ck.exists() else {}
    todo = [i for i in range(len(tasks)) if i not in done]
    chunk = chunk or max(workers * 12, 24)
    failures = 0
    while todo:
        batch = todo[:chunk]
        try:
            if workers <= 1:
                res = [fn(tasks[i]) for i in batch]
            else:
                with ProcessPoolExecutor(max_workers=workers) as ex:
                    res = list(ex.map(fn, [tasks[i] for i in batch]))
        except BrokenProcessPool:
            failures += 1
            if failures > 25:
                raise
            print(f"[{label}] worker pool broken, retrying chunk ({failures})", flush=True)
            continue
        done.update(zip(batch, res))
        todo = todo[chunk:]
        if ck:
            ck.parent.mkdir(parents=True, exist_ok=True)
            ck.write_bytes(pickle.dumps(done))
    print(f"[{label}] {len(tasks)} tasks in {time.time() - t0:.0f} s", flush=True)
    return [done[i] for i in range(len(tasks))]


def save(name: str, obj) -> pathlib.Path:
    path = RESULTS / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, default=_default))
    return path


def load(name: str):
    return json.loads((RESULTS / name).read_text())


def _default(o):
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, np.bool_):
        return bool(o)
    raise TypeError(type(o))


def first_mode(modes, building, direction: str = "x", tol: float = 0.05) -> dict:
    """Match the identified modes against the true first mode in one direction."""
    ms = building.modes[direction]
    f_true, z_true = float(ms.f[0]), float(ms.zeta[0])
    best = min(modes, key=lambda m: abs(m.f / f_true - 1), default=None)
    if best is None or abs(best.f / f_true - 1) > tol:
        return {"det": False, "f_err": None, "zeta_err": None, "z": None}
    return {"det": True, "f_err": best.f / f_true - 1, "zeta_err": best.zeta / z_true - 1, "z": best.z,
            "f_ci": [best.f_ci[0] / f_true - 1, best.f_ci[1] / f_true - 1],
            "zeta_ci": [best.zeta_ci[0] / z_true - 1, best.zeta_ci[1] / z_true - 1]}


def n_spurious(modes, building, tol: float = 0.05) -> int:
    """Identified peaks that match no true mode (any direction, any order)."""
    truth = [m["f"] for m in building.true_modes()]
    return sum(1 for m in modes if all(abs(m.f / f - 1) > tol for f in truth))


def mode_signal(building, env, phone, floor: int, direction: int = 0) -> dict:
    """Modal RMS (ug) at a floor and peak-to-noise power ratio in the horizontal trace."""
    from quakescore.sim.excitation import response_psd
    ms = building.modes["xy"[direction]]
    f1, z1 = float(ms.f[0]), float(ms.zeta[0])
    f = np.linspace(f1 * (1 - max(8 * z1, 0.1)), f1 * (1 + max(8 * z1, 0.1)), 2001)
    g = response_psd(building, env, f, floor)[:, direction, direction].real
    peak = float(g.max())
    return {"rms_ug": float(np.sqrt(np.trapezoid(g, f)) / UG), "peak_ug_rthz": float(np.sqrt(peak) / UG),
            "r": float(peak / (2 * phone.noise_psd(np.array([f1]))[0]))}
