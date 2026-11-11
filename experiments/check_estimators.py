"""Sanity check of every estimator at high and low SNR (not a reported experiment)."""
import dataclasses
import sys
import time

import numpy as np

from quakescore.ident.identify import identify, match_truth
from quakescore.sim.building import make_building
from quakescore.sim.excitation import ENVIRONMENTS
from quakescore.sim.fast import simulate_features
from quakescore.sim.phone import PHONE_MODELS, Placement

noise = float(sys.argv[1]) if len(sys.argv) > 1 else 2.0
env = ENVIRONMENTS[sys.argv[2] if len(sys.argv) > 2 else "energetic"]
rng = np.random.default_rng(5)
phone = dataclasses.replace(PHONE_MODELS["low"], noise_ug=noise, corner_hz=0.05 if noise < 20 else 0.5)
for n in (3, 9, 25, 40):
    b = make_building(n)
    sess = [simulate_features(b, env, Placement(phone, floor=n, yaw=rng.uniform(0, 6.28), contributor=f"c{i % 5}"),
                              6 * 3600, 0, rng) for i in range(20)]
    t0 = time.time()
    modes = identify(sess, n_boot=40, rng=rng, compare=True)
    dt = time.time() - t0
    print(f"N={n} ({dt:.1f}s) found {len(modes)}: " + " ".join(f"{m.f:.3f}" for m in modes))
    for r in match_truth(modes, [m for m in b.true_modes() if m["order"] == 1]):
        tm, m = r["truth"], r["mode"]
        if m is None:
            print(f"   {tm['dir']} f={tm['f']:.4f}: MISSED")
            continue
        a = m.alt
        print(f"   {tm['dir']} f={tm['f']:.4f} z={tm['zeta']:.4f} | fit {r['f_err']:+.4f} {r['zeta_err']:+.3f} snr={m.snr:.2f} z={m.z:.0f}"
              f" ci_f=({m.f_ci[0]/tm['f']-1:+.4f},{m.f_ci[1]/tm['f']-1:+.4f}) ci_z=({m.zeta_ci[0]/tm['zeta']-1:+.2f},{m.zeta_ci[1]/tm['zeta']-1:+.2f})"
              f" | fdd {a['fdd_peak']['f']/tm['f']-1:+.4f} | efdd {a['efdd']['f']/tm['f']-1:+.4f} {a['efdd']['zeta']/tm['zeta']-1:+.3f}"
              f" | ssi {a['ssi']['f']/tm['f']-1:+.4f} {a['ssi']['zeta']/tm['zeta']-1:+.3f}")
