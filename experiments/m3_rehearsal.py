"""Dress rehearsal for Milestone 3 with SIMULATED sessions. This is not a validation.

Builds simulated stand-ins for the reference buildings (published storeys and first-mode frequencies,
assumed damping and excitation), writes sessions as upload-schema files through the real codec, and
runs the Milestone 3 script on them. It checks the tooling end to end and shows what the table will
look like; it says nothing about how real buildings and real phones behave.
"""
from __future__ import annotations

import csv
import gzip
import json
import pathlib
import shutil
import subprocess
import sys
import uuid

import numpy as np

from common import RESULTS, ROOT, bands_for, seed_of
from quakescore.service.codec import encode
from quakescore.sim.building import Building
from quakescore.sim.excitation import ENVIRONMENTS
from quakescore.sim.fast import FastSite, simulate_features
from quakescore.sim.phone import PHONE_MODELS, random_placement

NIGHTS = 14


def main() -> None:
    out = RESULTS / "cache" / "rehearsal_sessions"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    refs = list(csv.DictReader((ROOT / "data" / "reference_buildings.csv").open(encoding="utf-8")))
    for ref in refs:
        rng = np.random.default_rng(seed_of("rehearsal", ref["building_id"]))
        f = sorted(float(v) for v in ref["f1_ref_hz"].split(";"))
        fx, fy = f[0], (f[1] if len(f) > 1 else f[0] * 1.15)
        n = int(ref["storeys"])
        zeta = float(np.clip(0.0143 * fx, 0.007, 0.04))
        height = float(ref["height_m"]) if ref["height_m"] else 3.3 * n
        b = Building(n, (fx, fy, fy * 1.3), (zeta, zeta, zeta), storey_height=height / n, building_id=ref["building_id"])
        bands = ("L", "M", "H")
        floor = max(1, int(round(0.8 * n)))
        sites = {e: FastSite(b, ENVIRONMENTS[e], floor, (0.0, 0.0), bands) for e in ("typical", "energetic")}
        for i in range(NIGHTS):
            env = str(rng.choice(["typical", "energetic"]))
            p = random_placement(rng, PHONE_MODELS[str(rng.choice(["low", "mid"]))], floor, contributor=f"{i % 4:016x}")
            p.pos = (0.0, 0.0)
            s = simulate_features(b, ENVIRONMENTS[env], p, 6 * 3600.0, 1.79e9 + 86400.0 * i, rng, site=sites[env],
                                  session_id=str(uuid.UUID(int=seed_of(ref["building_id"], i), version=4)))
            s.sync_source, s.floor_method = "ntp", "manual"        # the upload schema has no simulator values
            name = f"{ref['building_id'].replace(':', '_')}_{i:02d}.json.gz"
            (out / name).write_bytes(gzip.compress(json.dumps(encode(s)).encode()))
    subprocess.run([sys.executable, str(pathlib.Path(__file__).with_name("m3_validate_real.py")), str(out)], check=True)


if __name__ == "__main__":
    main()
