"""Figures for the technical note, drawn from the result files. Every figure is labelled SIM."""
from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from common import RESULTS, ROOT, load
from quakescore.features import band_freqs
from quakescore.ident.identify import identify
from quakescore.ident.stack import build_stack
from quakescore.sim.building import make_building
from quakescore.sim.excitation import ENVIRONMENTS
from quakescore.sim.fast import FastSite, simulate_features
from quakescore.sim.phone import PHONE_MODELS, random_placement

OUT = ROOT / "docs" / "pitch" / "figures"
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3de"
BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"   # validated categorical order
RAMP = ["#86b6ef", "#3987e5", "#256abf", "#104281"]                        # one-hue ordinal ramp
UG2 = (9.80665e-6) ** 2
PREFIX = (1, 2, 5, 10, 20, 50)

plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Segoe UI", "Helvetica Neue", "Arial", "DejaVu Sans"],
    "font.size": 9, "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "axes.titlesize": 10, "axes.titleweight": "semibold", "axes.titlecolor": INK, "axes.titlelocation": "left",
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "legend.frameon": False, "lines.linewidth": 2.0, "lines.markersize": 6.5, "axes.axisbelow": True,
})


def _save(fig, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fig.text(0.995, -0.035, "Simulated data", ha="right", va="top", fontsize=7.5, color=INK2)
    fig.savefig(OUT / name, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("wrote", name)


def fig_principle() -> None:
    rng = np.random.default_rng(21)
    b, env = make_building(9), ENVIRONMENTS["energetic"]
    site = FastSite(b, env, 9, (0.0, 0.0), ("M",))
    sess = []
    for i in range(20):
        p = random_placement(rng, PHONE_MODELS["low"], 9, soft_mount_prob=0.0, contributor=f"c{i % 4}")
        p.pos = (0.0, 0.0)
        sess.append(simulate_features(b, env, p, 6 * 3600.0, 86400.0 * i, rng, site=site, bands=("M",)))
    f = band_freqs("M")
    sel = (f > 1.1) & (f < 2.7)
    st = build_stack(sess, "M")
    noise = 2 * PHONE_MODELS["low"].noise_psd(f)
    modes = identify(sess, n_boot=0, bands=("M",))
    fig, ax = plt.subplots(figsize=(7.2, 3.3))
    ax.plot(f[sel], sess[0].trace("M")[sel] / UG2 / 1e3, color="#b9b8b2", lw=0.9, label="One night, one phone")
    ax.plot(f[sel], st.mean()[sel] / UG2 / 1e3, color=BLUE, label="20 nights stacked")
    ax.plot(f[sel], noise[sel] / UG2 / 1e3, color=INK2, lw=1.2, ls=(0, (4, 3)), label="Phone noise floor")
    for m in modes:
        if 1.1 < m.f < 2.7:
            ax.annotate(f"{m.f:.2f} Hz\ndamping {100 * m.zeta:.1f}%", (m.f, st.mean()[int(round(m.f / f[1]))] / UG2 / 1e3),
                        xytext=(0, 14), textcoords="offset points", ha="center", fontsize=8, color=INK,
                        arrowprops={"arrowstyle": "-", "color": INK2, "lw": 0.8})
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("Horizontal power spectral density\n(thousand ug^2/Hz)")
    ax.set_title("The building's modes sit below the phone's own noise and appear only after stacking")
    ax.set_ylim(noise[sel].min() / UG2 / 1e3 * 0.82, noise[sel].max() / UG2 / 1e3 * 1.75)
    ax.legend(loc="upper right", ncol=3, fontsize=8)
    _save(fig, "fig1_principle.png")


def _needed(recs, tol=0.02, need=0.9):
    for ns in PREFIX:
        ok = [r["by_n"][str(ns)]["x"]["det"] and abs(r["by_n"][str(ns)]["x"]["f_err"]) <= tol for r in recs]
        if np.mean(ok) >= need:
            return ns
    return None


def fig_detection() -> None:
    e3 = load("m1/e3_detection_limit.json")
    cfg: dict = {}
    for r in e3:
        cfg.setdefault((r["n"], r["env"], r["phone"], r["frac"]), []).append(r)
    heights = sorted({k[0] for k in cfg})
    fig, axes = plt.subplots(1, 3, figsize=(7.4, 3.0), sharey=True)
    ypos = {1: 0, 2: 1, 5: 2, 10: 3, 20: 4, 50: 5, None: 6}
    names = {"low": "80 ug/sqrt(Hz) phone", "mid": "150 ug/sqrt(Hz) phone", "high": "300 ug/sqrt(Hz) phone"}
    for ax, env in zip(axes, ("quiet", "typical", "energetic")):
        ax.axhspan(5.5, 6.5, color="#f1f0ec", zorder=0)
        for phone, col, mk in (("low", BLUE, "o"), ("mid", ORANGE, "s"), ("high", AQUA, "^")):
            ys = [ypos[_needed(cfg[(n, env, phone, 1.0)])] for n in heights]
            x = np.arange(len(heights))
            ax.plot(x, ys, color=col, marker=mk, label=names[phone], markeredgecolor=SURFACE, markeredgewidth=1.2)
        ax.set_xticks(np.arange(len(heights)), [str(h) for h in heights])
        ax.set_yticks(list(range(7)), ["1", "2", "5", "10", "20", "50", "not reached"])
        ax.set_ylim(-0.5, 6.5)
        ax.set_title({"quiet": "Quiet night", "typical": "Typical night", "energetic": "Windy / busy night"}[env])
        ax.set_xlabel("Storeys")
    axes[0].set_ylabel("Nights needed for a stable first mode")
    axes[0].legend(loc="lower left", fontsize=7.5, bbox_to_anchor=(0.0, 1.14), ncol=3, columnspacing=1.2)
    fig.suptitle("Detection is governed by excitation and phone noise far more than by height", x=0.01, y=1.17, ha="left",
                 fontsize=10, fontweight="semibold", color=INK)
    _save(fig, "fig2_detection_limit.png")


def fig_methods() -> None:
    e2 = load("m1/e2_methods.json")
    hit = [m for r in e2 for m in r["modes"].values() if m["fit"] is not None]
    lo, hi = [m for m in hit if m["snr"] < 1], [m for m in hit if m["snr"] >= 1]

    def med(g, key, i):
        v = [abs(m[key][i]) for m in g if m[key][i] is not None and np.isfinite(m[key][i])]
        return 100 * float(np.median(v)) if v else np.nan

    fig, axes = plt.subplots(1, 2, figsize=(7.4, 2.7))
    rows = {0: [("Spectral curve fit", "fit"), ("SSI-COV", "ssi"), ("EFDD", "efdd"), ("FDD peak pick", "fdd_peak")],
            1: [("Spectral curve fit", "fit"), ("SSI-COV", "ssi"), ("EFDD", "efdd"), ("Random decrement", "rdt")]}
    for i, ax in enumerate(axes):
        labels = [r[0] for r in rows[i]][::-1]
        for g, col, mk, name in ((lo, ORANGE, "s", "Peak below the noise floor"), (hi, BLUE, "o", "Peak above the noise floor")):
            vals = [med(g, key, i) for _, key in rows[i]][::-1]
            ax.scatter(vals, range(len(labels)), color=col, marker=mk, s=52, label=name, zorder=3, edgecolor=SURFACE, linewidth=1.2)
            dy = 9 if g is lo else -15                       # labels above one series and below the other
            for v, y in zip(vals, range(len(labels))):
                txt = f"{v:.0f}%" if v >= 10 else (f"{v:.1f}%" if v >= 1 else f"{v:.2f}%")
                ax.annotate(txt, (v, y), xytext=(0, dy), textcoords="offset points", ha="center", fontsize=7.5, color=INK)
        ax.set_yticks(range(len(labels)), labels)
        ax.set_xscale("log")
        ticks = [0.03, 0.1, 0.3, 1.0] if i == 0 else [3, 10, 30, 100, 300]
        ax.set_xticks(ticks, [f"{t:g}" for t in ticks])
        ax.set_xticks([], minor=True)
        ax.set_xlim(ticks[0], ticks[-1])
        ax.set_ylim(-0.7, len(labels) - 0.3)
        ax.set_xlabel("Median absolute error (%), log scale")
        ax.set_title(("Frequency", "Damping")[i])
        ax.grid(axis="y", visible=False)
    axes[0].legend(loc="lower left", fontsize=7.5, bbox_to_anchor=(0.0, 1.14), ncol=2)
    fig.suptitle("The curve fit is the only estimator that holds up when the mode is buried in sensor noise", x=0.01, y=1.2,
                 ha="left", fontsize=10, fontweight="semibold", color=INK)
    fig.subplots_adjust(wspace=0.55)
    _save(fig, "fig3_methods.png")


def fig_change() -> None:
    m6 = load("m6/change_detection.json")["summary"]
    rows = [r for r in m6 if r["storeys"] == 9 and r["phone"] == "low"]
    fig, ax = plt.subplots(figsize=(5.4, 3.0))
    xs = [2.5, 5, 10, 20]
    for r, col in zip(sorted(rows, key=lambda r: r["epochs"]), RAMP):
        ys = [100 * r["detect"][k] for k in ("0.025", "0.05", "0.1", "0.2")]
        ax.plot(range(4), ys, color=col, marker="o", markeredgecolor=SURFACE, markeredgewidth=1.2,
                label=f"{r['sessions_total']} sessions in the year")
    ax.axhline(90, color=INK2, lw=0.9, ls=(0, (4, 3)))
    ax.text(3.02, 91, "90%", fontsize=7.5, color=INK2, va="bottom", ha="right")
    ax.set_xticks(range(4), [f"{x:g}%" for x in xs])
    ax.set_ylim(-3, 104)
    ax.set_xlabel("Permanent stiffness loss half-way through the year")
    ax.set_ylabel("Detected (%), at 5% false alarms")
    ax.set_title("Stiffness loss detected, 9-storey building, 80 ug/sqrt(Hz) phones")
    ax.legend(loc="lower right", fontsize=7.5)
    _save(fig, "fig4_change_detection.png")


def fig_city() -> None:
    s = json.loads((RESULTS / "demo_city" / "summary.json").read_text())
    groups = list(s["by_storeys"])
    fig, ax = plt.subplots(figsize=(5.6, 2.9))
    w = 0.25
    for j, (key, col, name) in enumerate((("buildings", "#b9b8b2", "Footprints"), ("with_sessions", ORANGE, "With at least one session"),
                                          ("scored", BLUE, "Scored"))):
        vals = [s["by_storeys"][g][key] for g in groups]
        bars = ax.bar(np.arange(len(groups)) + (j - 1) * (w + 0.02), vals, w, color=col, label=name)
        for b_, v in zip(bars, vals):
            ax.annotate(str(v), (b_.get_x() + b_.get_width() / 2, v), xytext=(0, 2), textcoords="offset points", ha="center",
                        fontsize=7.5, color=INK)
    ax.set_xticks(range(len(groups)), groups)
    ax.set_xlabel("Storeys")
    ax.set_ylabel("Buildings")
    ax.grid(axis="x", visible=False)
    ax.set_title("Demo district: coverage follows building size under the assumed adoption")
    ax.legend(fontsize=7.5, loc="upper right")
    _save(fig, "fig5_demo_city.png")


if __name__ == "__main__":
    import sys
    todo = sys.argv[1:] or ["principle", "detection", "methods", "change", "city"]
    for name in todo:
        globals()[f"fig_{name}"]()
