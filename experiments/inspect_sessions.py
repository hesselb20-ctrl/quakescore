"""Look at real session files pulled from a phone: what was recorded and which peaks it shows.

Usage: python experiments/inspect_sessions.py <folder with session .json files>

Session files are the upload schema v1, exactly as the app stores them. For each building in the
folder this prints the sessions (phone, floor, duration, windows kept, noise floor) and every
candidate peak with its label from the artefact tests. It needs no reference values, so it is the
first thing to run after a test night. Compare against published values with m3_validate_real.py.

How to get the files off a phone running the debug build (no server needed):
    adb exec-out run-as org.quakescore.collector tar c files/sessions > sessions.tar
    tar xf sessions.tar
    python experiments/inspect_sessions.py files/sessions
Run the adb line from cmd or Git Bash, not PowerShell, which corrupts binary redirects.
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np

from m3_validate_real import load_sessions
from quakescore.artefacts.reject import apply
from quakescore.features import BANDS, band_freqs
from quakescore.ident.identify import identify

UG = 9.80665e-6


def noise_floor_ug(session, band: str = "H") -> float:
    """Median horizontal noise density in ug/sqrt(Hz) over a band's search range (per axis)."""
    f = band_freqs(band)
    lo, hi = BANDS[band]["search"]
    sel = (f >= lo) & (f <= hi)
    if session.bands[band].k < 3:
        return float("nan")
    return float(np.sqrt(np.median(session.trace(band)[sel]) / 2) / UG)


def main() -> None:
    folder = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path("files/sessions")
    if not folder.exists():
        print(f"No folder {folder}. See the usage note at the top of this file.")
        return
    by_building = load_sessions(folder)
    if not by_building:
        print(f"No session files in {folder}.")
        return
    for bid, sessions in by_building.items():
        prov = sorted({s.provenance for s in sessions})
        print(f"\n== {bid}: {len(sessions)} session(s), provenance {', '.join(prov)}")
        print("   phone | floor | hours | windows kept L/M/H | accepted | noise floor ug/rtHz (5-18 Hz) | sync")
        for s in sessions:
            k = "/".join(str(s.bands[b].k) for b in "LMH")
            print(f"   {s.phone_model[:24]:24s} | {s.floor:3d} | {s.duration / 3600:5.2f} | {k:14s} | "
                  f"{100 * s.accept_fraction:5.1f}% | {noise_floor_ug(s):7.1f} | {s.sync_source} +-{s.sync_sigma_ms:.0f} ms")
        modes = apply(identify(sessions, n_boot=200 if len(sessions) >= 2 else 0, rng=np.random.default_rng(0)))
        if not modes:
            print("   no candidate peaks above the detection threshold")
            continue
        print("   f (Hz) | 90% interval | damping | score | label")
        for m in modes:
            ci = "-" if not np.isfinite(m.f_ci[0]) else f"{m.f_ci[0]:.3f}-{m.f_ci[1]:.3f}"
            print(f"   {m.f:6.3f} | {ci:13s} | {100 * m.zeta:5.2f}% | {m.z:5.1f} | {m.label}")
    print("\nA single night rarely shows a building mode. The noise floor column is already a result: it is the "
          "number the detection-limit tables depend on most.")


if __name__ == "__main__":
    main()
