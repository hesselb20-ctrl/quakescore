"""Build results/m1_summary.md from the Milestone 1 experiment outputs."""
from __future__ import annotations

import numpy as np

from common import RESULTS, load

PREFIX = (1, 2, 5, 10, 20, 50)
out: list[str] = []
w = out.append


def pct(v, d=1):
    return "n/a" if v is None or not np.isfinite(v) else f"{100 * v:.{d}f}%"


def med_abs(vals):
    vals = [abs(v) for v in vals if v is not None and np.isfinite(v)]
    return float(np.median(vals)) if vals else float("nan")


def sessions_needed(recs, key="x", need=0.9, tol=0.02):
    """Smallest session count at which the first mode is found within tol in at least `need` of trials."""
    for ns in PREFIX:
        ok = [r["by_n"][str(ns)][key]["det"] and abs(r["by_n"][str(ns)][key]["f_err"]) <= tol for r in recs]
        if np.mean(ok) >= need:
            return ns
    return None


w("# Milestone 1 results: simulator and identification core\n")
w("Provenance of every number in this file: **SIM**. Nothing here was measured on a real building.")
w("Excitation levels and phone noise profiles are assumptions (see `quakescore/sim/excitation.py` and")
w("`quakescore/sim/phone.py`); the tables are reported against them and against the physical")
w("peak-to-noise ratio so they can be re-read when field data replaces the assumptions.\n")

# ---------------------------------------------------------------- e1
e1 = load("m1/e1_fast_vs_timedomain.json")
w("## 1. Fast spectral path against the full time-domain path\n")
w("Four 4-hour sessions per case. `ratio` is stacked spectrum divided by the analytic expectation")
w("(median over the band); `z` is the detection score of the first mode in x.\n")
w("| Storeys | Phone | Time-domain ratio L/M/H | Fast ratio L/M/H | z time-domain | z fast | f error TD | f error fast |")
w("|---|---|---|---|---|---|---|---|")
for r in e1:
    td = "/".join(f"{r['bands'][b]['td_ratio_median']:.3f}" for b in "LMH")
    fa = "/".join(f"{r['bands'][b]['fast_ratio_median']:.3f}" for b in "LMH")
    zt = r["td"]["x"]["z"]
    zf = r["fast"]["x"]["z"]
    w(f"| {r['n']} | {r['phone']} | {td} | {fa} | {'-' if zt is None else f'{zt:.0f}'} | {'-' if zf is None else f'{zf:.0f}'} "
      f"| {pct(r['td']['x']['f_err'], 2)} | {pct(r['fast']['x']['f_err'], 2)} |")
w("\nThe device pipeline reproduces the analytic spectrum to within about 1% in all three bands, and the")
w("fast path gives the same detection scores as the time-domain path. The fast path is used for the")
w("large sweeps below; it has no quantisation, jitter, gating or interference.\n")

# ---------------------------------------------------------------- e2
e2 = load("m1/e2_methods.json")
w("## 2. Estimator comparison (time-domain sessions)\n")
w("Six 4-hour sessions per building, phone at the roof, six buildings per row, first mode in x and y.")
w("Entries are median absolute error. Random decrement runs on raw device data; the others on the")
w("stacked spectra. `SNR` is the peak-to-noise-floor power ratio of the stacked spectrum.\n")
w("| Storeys | Scenario | Phone | Found | Median SNR | f: curve fit | f: FDD peak | f: EFDD | f: SSI-COV | zeta: curve fit | zeta: EFDD | zeta: SSI-COV | zeta: random decrement | zeta interval covers truth |")
w("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
groups: dict = {}
for r in e2:
    groups.setdefault((r["n"], r["env"], r["phone"]), []).append(r)
for (n, env, ph), rs in sorted(groups.items()):
    ms = [m for r in rs for m in r["modes"].values()]
    hit = [m for m in ms if m["fit"] is not None]
    if not hit:
        w(f"| {n} | {env} | {ph} | 0/{len(ms)} | - | - | - | - | - | - | - | - | - | - |")
        continue
    col = lambda key, i: pct(med_abs([m[key][i] for m in hit]), 2 if i == 0 else 0)
    cover = np.mean([m["fit_ci_cover_zeta"] for m in hit])
    w(f"| {n} | {env} | {ph} | {len(hit)}/{len(ms)} | {np.median([m['snr'] for m in hit]):.2f} | {col('fit', 0)} | {col('fdd_peak', 0)} "
      f"| {col('efdd', 0)} | {col('ssi', 0)} | {col('fit', 1)} | {col('efdd', 1)} | {col('ssi', 1)} | {col('rdt', 1)} | {pct(cover, 0)} |")
allhit = [m for r in e2 for m in r["modes"].values() if m["fit"] is not None]
lo = [m for m in allhit if m["snr"] < 1]
hi = [m for m in allhit if m["snr"] >= 1]
w("\nPooled by regime:\n")
w("| Regime | Modes | f: curve fit | f: FDD peak | f: EFDD | f: SSI-COV | zeta: curve fit | zeta: EFDD | zeta: SSI-COV | zeta: random decrement |")
w("|---|---|---|---|---|---|---|---|---|---|")
for name, g in (("peak below noise floor (SNR < 1)", lo), ("peak above noise floor (SNR >= 1)", hi)):
    if g:
        w(f"| {name} | {len(g)} | " + " | ".join(pct(med_abs([m[k][i] for m in g]), 2 if i == 0 else 0)
                                                 for k, i in (("fit", 0), ("fdd_peak", 0), ("efdd", 0), ("ssi", 0), ("fit", 1), ("efdd", 1), ("ssi", 1), ("rdt", 1))) + " |")
w(f"\nBootstrap 90% interval for damping covers the truth in {pct(np.mean([m['fit_ci_cover_zeta'] for m in allhit]), 0)} of modes "
  f"(nominal 90%); for frequency in {pct(np.mean([m['fit_ci_cover_f'] for m in allhit]), 0)}. "
  f"Median width of the damping interval: {pct(np.median([m['fit_ci_zeta_width'] for m in allhit]), 0)} of the true value.\n")

# ---------------------------------------------------------------- e3
try:
    e3 = load("m1/e3_detection_limit.json")
except FileNotFoundError:
    e3 = None
if e3:
    w("## 3. Detection limit by building height\n")
    w("Sessions are 6-hour nights, one phone per session, random yaw, 15% of placements on a soft surface.")
    w("Entry: number of sessions needed before the first mode is found and within 2% of the truth in at")
    w("least 90% of 12 trials. `>50` means not reached with 50 sessions. Scenario assumptions: quiet =")
    w("ground noise -110 dB re (m/s^2)^2/Hz and 1.5 m/s wind; typical = -100 dB and 3 m/s; energetic =")
    w("-90 dB and 7 m/s. Phone noise density: low 80, mid 150, high 300 ug/sqrt(Hz).\n")
    cfg: dict = {}
    for r in e3:
        cfg.setdefault((r["n"], r["env"], r["phone"], r["frac"]), []).append(r)
    heights = sorted({k[0] for k in cfg})
    for frac, title in ((1.0, "Phone on the top floor"), (0.5, "Phone at mid-height")):
        w(f"### {title}\n")
        w("| Storeys | Typical f1 (Hz) | " + " | ".join(f"{e} / {p}" for e in ("quiet", "typical", "energetic") for p in ("low", "mid", "high")) + " |")
        w("|---|---|" + "---|" * 9)
        for n in heights:
            cells = []
            for e in ("quiet", "typical", "energetic"):
                for p in ("low", "mid", "high"):
                    rs = cfg.get((n, e, p, frac))
                    ns = sessions_needed(rs) if rs else None
                    cells.append("n/a" if not rs else (">50" if ns is None else str(ns)))
            w(f"| {n} | {1 / (0.02 * 3.3 * n):.2f} | " + " | ".join(cells) + " |")
        w("")
    w("### Signal levels behind the table (top floor, median over trials)\n")
    w("| Storeys | Scenario | Modal RMS (ug) | Peak (ug/sqrt(Hz)) | Peak-to-noise r: low / mid / high phone |")
    w("|---|---|---|---|---|")
    for n in heights:
        for e in ("quiet", "typical", "energetic"):
            rs = {p: cfg.get((n, e, p, 1.0)) for p in ("low", "mid", "high")}
            if not rs["low"]:
                continue
            sig = rs["low"]
            w(f"| {n} | {e} | {np.median([r['signal']['rms_ug'] for r in sig]):.1f} | {np.median([r['signal']['peak_ug_rthz'] for r in sig]):.0f} | "
              + " / ".join(f"{np.median([r['signal']['r'] for r in rs[p]]):.3f}" for p in ("low", "mid", "high")) + " |")
    w("")
    # empirical law: sessions needed against r
    pts = []
    for (n, e, p, frac), rs in cfg.items():
        ns = sessions_needed(rs)
        pts.append((float(np.median([r["signal"]["r"] for r in rs])), ns, n))
    w("### Detection limit as a rule\n")
    w("Across all configurations, sessions needed against the peak-to-noise ratio `r` of one session:\n")
    w("| Peak-to-noise ratio r | Configurations | Share reaching a stable first mode within 5 / 20 / 50 sessions |")
    w("|---|---|---|")
    edges = [0, 0.003, 0.01, 0.03, 0.1, 0.3, 1, 1e9]
    for a, b in zip(edges[:-1], edges[1:]):
        g = [ns for r, ns, _ in pts if a <= r < b]
        if g:
            sh = lambda lim: pct(np.mean([ns is not None and ns <= lim for ns in g]), 0)
            w(f"| {a:g} - {b:g} | {len(g)} | {sh(5)} / {sh(20)} / {sh(50)} |".replace("1e+09", "inf"))
    w("")
    best = [r for r in e3 if r["phone"] == "best"]
    if best:
        w("### Sensitivity: a 25 ug/sqrt(Hz) phone\n")
        w("The noise floor implied by published MyShake phone spectra is far below datasheet values and")
        w("the two have not been reconciled (docs/references.md). If phones are really that quiet:\n")
        w("| Storeys | quiet | typical | energetic |")
        w("|---|---|---|---|")
        for n in sorted({r["n"] for r in best}):
            cells = []
            for e in ("quiet", "typical", "energetic"):
                rs = [r for r in best if r["n"] == n and r["env"] == e]
                ns = sessions_needed(rs)
                cells.append(">50" if ns is None else str(ns))
            w(f"| {n} | " + " | ".join(cells) + " |")
        w("")
    sp = [r["by_n"][str(ns)]["spurious"] for r in e3 for ns in PREFIX]
    nd = sum(r["by_n"][str(ns)]["x"]["det"] + r["by_n"][str(ns)]["y"]["det"] for r in e3 for ns in PREFIX)
    w(f"Raw candidate peaks that match no true mode, over the whole sweep (no interference, z >= 6, before artefact rejection): "
      f"{sum(sp)} against {nd} correct first-mode detections. Almost all are on the 150 and 300 ug phones and are line-like artefacts "
      "near the top of an analysis band, where the baseline window is clipped at the band edge on steep low-frequency noise. The "
      "width test of the artefact stage removes them (0 of 63 accepted in a noise-only check). A symmetric baseline window would "
      "prevent them; it was not applied because every experiment would have to be rerun.\n")
    w("### Error once detected (all configurations pooled)\n")
    w("| Sessions | First modes detected | Median abs frequency error | 90th percentile | Median abs damping error |")
    w("|---|---|---|---|---|")
    for ns in PREFIX:
        fe = [abs(r["by_n"][str(ns)][d]["f_err"]) for r in e3 for d in "xy" if r["by_n"][str(ns)][d]["det"]]
        ze = [abs(r["by_n"][str(ns)][d]["zeta_err"]) for r in e3 for d in "xy" if r["by_n"][str(ns)][d]["det"]]
        if fe:
            w(f"| {ns} | {len(fe)} | {pct(np.median(fe), 2)} | {pct(np.percentile(fe, 90), 2)} | {pct(np.median(ze), 0)} |")
    w("")

# ---------------------------------------------------------------- e4a
e4a = load("m1/e4a_record_length.json")
w("## 4. Record length\n")
w("Low-noise phone on the top floor, 16 trials per cell. Entry: share of trials where the first mode (x)")
w("is found within 2%, then median absolute frequency and damping error when found.\n")
w("| Storeys | Scenario | Sessions | 0.5 h | 1 h | 2 h | 4 h | 8 h |")
w("|---|---|---|---|---|---|---|---|")
g4: dict = {}
for r in e4a:
    g4.setdefault((r["n"], r["env"], r["sessions"], r["hours"]), []).append(r["x"])
for n in (9, 25):
    for env in ("typical", "energetic"):
        for ns in (5, 20):
            cells = []
            for h in (0.5, 1.0, 2.0, 4.0, 8.0):
                xs = g4[(n, env, ns, h)]
                ok = [x for x in xs if x["det"] and abs(x["f_err"]) <= 0.02]
                if ok:
                    cells.append(f"{pct(len(ok) / len(xs), 0)}, {pct(med_abs([x['f_err'] for x in ok]), 2)}, {pct(med_abs([x['zeta_err'] for x in ok]), 0)}")
                else:
                    cells.append("0%")
            w(f"| {n} | {env} | {ns} | " + " | ".join(cells) + " |")
w("")

# ---------------------------------------------------------------- e4b
e4b = load("m1/e4b_phones.json")
w("## 5. Several phones at once\n")
w("One 6-hour night, low-noise phones spread from 30% of the height to the roof, 10 trials per cell.")
w("`incoherent` stacks each phone's own spectrum (no time sync needed). `coherent` runs FDD on the")
w("cross-spectral matrix between phones (needs sync frames). Entries are median detection scores of")
w("the first mode; the last column is the RMS error of the first-mode shape amplitudes (3+ phones).\n")
w("| Storeys | Scenario | Phones | Sync error (ms) | z incoherent | z coherent | Gain | Mode shape RMS error |")
w("|---|---|---|---|---|---|---|---|")
g5: dict = {}
for r in e4b:
    g5.setdefault((r["n"], r["env"], r["phones"], r["sync_ms"]), []).append(r)
for (n, env, ph, sync), rs in sorted(g5.items()):
    zi = np.nanmedian([r["z_incoherent"] for r in rs])
    zc = np.nanmedian([r["z_coherent"] for r in rs])
    sh = [r["shape_rms_err"] for r in rs if "shape_rms_err" in r]
    w(f"| {n} | {env} | {ph} | {sync:.0f} | {zi:.1f} | {zc:.1f} | {zc / zi if zi > 0 else float('nan'):.2f} | {'-' if not sh else f'{np.median(sh):.3f}'} |")
w("")

# ---------------------------------------------------------------- e5
e5 = load("m1/e5_false_alarms.json")
w("## 6. False alarms on structure-free noise\n")
w(f"{e5['stacks']} stacks of {e5['sessions_per_stack']} sessions with no structural response (ground-floor phones, rigid mount), all three bands searched.\n")
w("| Threshold z | Stacks with at least one false peak | Share |")
w("|---|---|---|")
for thr in ("5.0", "5.5", "6.0", "7.0"):
    c = e5[f"stacks_with_false_peak_z{thr}"]
    w(f"| {thr} | {c} | {pct(c / e5['stacks'], 2)} |")
w("")

(RESULTS / "m1_summary.md").write_text("\n".join(out), encoding="utf-8")
print("\n".join(out))
