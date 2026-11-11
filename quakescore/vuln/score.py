"""Structural class, stiffness anomaly and QuakeScore for one building."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .fragility import DAMAGE_STATES, SCENARIOS, family, mean_damage_ratio, system, tables

SIGMA_LN_T = 0.25      # scatter of measured period about a class relation (ASSUMED from published se of 0.21-0.23)

# Expected ambient-level period T = a * H^b, H in metres. Provenance per entry in docs/references.md:
# C2 Michel et al. 2010; C3 Ditommaso et al. 2013; C1 and S1 AIJ low-amplitude data (indicative);
# the rest ASSUMED (wall types follow C2; URM and wood use 0.05 H^0.75 divided by 1.6).
AMBIENT_PERIOD = {
    "C1": (0.018, 1.0), "C2": (0.013, 1.0), "C3": (0.016, 1.0), "S1": (0.024, 1.0), "S2": (0.020, 1.0),
    "PC2": (0.013, 1.0), "RM1": (0.013, 1.0), "RM2": (0.013, 1.0), "URM": (0.03125, 0.75), "W1": (0.03125, 0.75),
}
# Expected ambient damping ratio = c * f1 (AIJ low-amplitude data via Tamura; indicative), capped
AMBIENT_DAMPING = {"C": 0.0143, "PC": 0.0143, "RM": 0.0143, "URM": 0.0143, "W": 0.0143, "S": 0.013}

# Class mix by region and height class (ASSUMED, illustrative; replace with an exposure model)
REGION_MIX = {
    "us_west": {
        "L": {"W1": 0.55, "RM1L": 0.12, "C2L": 0.10, "S1L": 0.08, "S2L": 0.07, "C1L": 0.05, "URML": 0.03},
        "M": {"C2M": 0.30, "S1M": 0.20, "S2M": 0.15, "C1M": 0.15, "RM2M": 0.10, "PC2M": 0.05, "C3M": 0.05},
        "H": {"S1H": 0.35, "C2H": 0.30, "S2H": 0.20, "C1H": 0.15},
    },
    "europe_south": {
        "L": {"URML": 0.45, "C3L": 0.30, "C1L": 0.15, "C2L": 0.10},
        "M": {"C3M": 0.40, "C1M": 0.30, "C2M": 0.15, "URMM": 0.15},
        "H": {"C2H": 0.40, "C1H": 0.35, "C3H": 0.25},
    },
}
# Design level by construction year (ASSUMED; Hazus gives guidance by seismic zone and age)
CODE_ERAS = {
    "us_west": ((1941, "pre"), (1976, "moderate"), (9999, "high")),
    "europe_south": ((1975, "pre"), (2000, "low"), (9999, "moderate")),
}
MATERIAL_FAMILY = {"concrete": ("C", "PC"), "reinforced_concrete": ("C", "PC"), "steel": ("S",), "wood": ("W",),
                   "timber": ("W",), "brick": ("URM", "RM"), "masonry": ("URM", "RM"), "stone": ("URM",)}
GEM = {"C1": "CR/LFM", "C2": "CR/LWAL", "C3": "CR/LFINF", "S1": "S/LFM", "S2": "S/LFBR", "W1": "W/LWAL",
       "URM": "MUR/LWAL", "RM1": "MR/LWAL", "RM2": "MR/LWAL", "PC2": "CR+PC/LWAL"}


@dataclass
class Attributes:
    height_m: float
    storeys: int
    year: int | None = None
    material: str | None = None
    region: str = "us_west"


@dataclass
class Measurement:
    f1: float
    f1_ci: tuple[float, float]
    zeta: float | None = None
    zeta_ci: tuple[float, float] | None = None
    dcf_ratio: float | None = None                 # measured / reference drift concentration
    dcf_ci: tuple[float, float] | None = None


@dataclass
class ScoreResult:
    score: float
    lo: float
    hi: float
    class_probs: dict[str, float]
    class_map: str
    gem_taxonomy: str
    damage: dict[str, dict[str, float]]
    k_ratio: float | None = None
    anomaly_z: float | None = None
    anomaly_flag: bool = False
    detail: dict = field(default_factory=dict)


def height_class(storeys: int) -> str:
    return "L" if storeys <= 3 else ("M" if storeys <= 7 else "H")


def expected_period(btype: str, height_m: float) -> float:
    a, b = AMBIENT_PERIOD[system(btype) if system(btype) in AMBIENT_PERIOD else family(btype)]
    return a * height_m**b


def class_prior(attrs: Attributes) -> dict[str, float]:
    mix = dict(REGION_MIX[attrs.region][height_class(attrs.storeys)])
    if attrs.storeys > 2:
        mix.pop("W1", None)
    if attrs.material and attrs.material.lower() in MATERIAL_FAMILY:
        fams = MATERIAL_FAMILY[attrs.material.lower()]
        mix = {k: v * (20.0 if family(k) in fams else 1.0) for k, v in mix.items()}
    tot = sum(mix.values())
    return {k: v / tot for k, v in mix.items() if k in tables()}


def code_levels(attrs: Attributes) -> dict[str, float]:
    eras = CODE_ERAS[attrs.region]
    if attrs.year is None:
        names = [e[1] for e in eras]
        return {n: 1.0 / len(names) for n in names}
    return {next(lvl for limit, lvl in eras if attrs.year < limit): 1.0}


def class_posterior(attrs: Attributes, period: float | None) -> dict[str, float]:
    """Bayes update of the class prior with the likelihood of the measured period."""
    prior = class_prior(attrs)
    if period is None:
        return prior
    like = {k: np.exp(-0.5 * (np.log(period / expected_period(k, attrs.height_m)) / SIGMA_LN_T) ** 2)
            for k in prior}
    post = {k: prior[k] * like[k] for k in prior}
    tot = sum(post.values())
    return {k: v / tot for k, v in post.items()} if tot > 0 else prior


def stiffness_anomaly(attrs: Attributes, period: float) -> tuple[float, float, bool, str]:
    """Stiffness ratio and z-score under the most probable class, and the all-classes flag.

    The flag is raised only if the building is softer than expected by more than 2 sigma under
    every class with a prior above 10%, because class and stiffness are otherwise confounded.
    """
    prior = class_prior(attrs)
    post = class_posterior(attrs, period)
    best = max(post, key=post.get)
    t_exp = expected_period(best, attrs.height_m)
    z_all = [np.log(period / expected_period(k, attrs.height_m)) / SIGMA_LN_T for k, v in prior.items() if v >= 0.10]
    return float((t_exp / period) ** 2), float(np.log(period / t_exp) / SIGMA_LN_T), bool(min(z_all) > 2.0), best


def mode_order_probability(attrs: Attributes, f: float, ratio: float = 2.8, miss_prior: float = 0.25) -> float:
    """Probability that the lowest identified mode at frequency f is the fundamental.

    The alternative is that the fundamental was missed and f is the second mode (f2/f1 is about 2.8
    for shear-type buildings). Uses the height-based period prior over the plausible classes.
    """
    prior = class_prior(attrs)

    def dens(period: float) -> float:
        return sum(p * np.exp(-0.5 * (np.log(period / expected_period(c, attrs.height_m)) / SIGMA_LN_T) ** 2)
                   for c, p in prior.items())

    l1, l2 = dens(1.0 / f), dens(ratio / f)
    return float(l1 / max(l1 + miss_prior * l2, 1e-300))


def _lognormal(rng, value: float, ci: tuple[float, float] | None, n: int) -> np.ndarray:
    if ci is None or not np.all(np.isfinite(ci)) or ci[0] <= 0:
        return np.full(n, value)
    return value * np.exp(rng.normal(0, max(np.log(ci[1] / ci[0]) / 3.29, 1e-6), n))


def quakescore(attrs: Attributes, m: Measurement | None = None, n_mc: int = 300,
               rng: np.random.Generator | None = None) -> ScoreResult:
    """QuakeScore = 100 * (1 - scenario-weighted structural mean damage ratio), with a 5-95% band.

    Without a measurement the band reflects class, design level and period scatter. With a
    measurement the period is known, so that part of the band collapses to the measurement interval.
    """
    rng = rng or np.random.default_rng(0)
    period = None if m is None else 1.0 / m.f1
    post = class_posterior(attrs, period)
    levels = code_levels(attrs)
    names, pc = list(post), np.array(list(post.values()))
    lnames, pl = list(levels), np.array(list(levels.values()))
    cls = rng.choice(len(names), n_mc, p=pc)
    lvl = rng.choice(len(lnames), n_mc, p=pl)
    if m is None:
        t_ratio = np.exp(rng.normal(0, SIGMA_LN_T, n_mc))
        dcf = np.ones(n_mc)
        zeta_s = None
    else:
        t_meas = 1.0 / _lognormal(rng, m.f1, m.f1_ci, n_mc)
        t_ratio = None
        dcf = np.ones(n_mc) if m.dcf_ratio is None else _lognormal(rng, m.dcf_ratio, m.dcf_ci, n_mc)
        tight = m.zeta is not None and m.zeta_ci is not None and m.zeta_ci[0] > 0 and m.zeta_ci[1] / m.zeta_ci[0] < 1.8
        zeta_s = _lognormal(rng, m.zeta, m.zeta_ci, n_mc) if tight else None
    mdr = np.empty(n_mc)
    probs = np.zeros((len(SCENARIOS), 4))
    cache: dict = {}
    for i in range(n_mc):
        bt, lv = names[cls[i]], lnames[lvl[i]]
        if "median_in" not in tables()[bt]["levels"].get(lv, {}):
            lv = "pre"
        tr = t_ratio[i] if t_ratio is not None else t_meas[i] / expected_period(bt, attrs.height_m)
        dr = 1.0
        if zeta_s is not None:
            dr = float(np.clip(zeta_s[i] / min(AMBIENT_DAMPING[family(bt)] * m.f1, 0.05), 0.4, 2.5))
        key = (bt, lv, round(float(tr), 3), round(float(dcf[i]), 3), round(dr, 2))
        if key not in cache:
            cache[key] = mean_damage_ratio(bt, lv, attrs.height_m, t_ratio=float(tr),
                                           dcf_ratio=float(max(dcf[i], 0.5)), damping_ratio=dr)
        mdr[i], pr = cache[key]
        probs += pr
    probs /= n_mc
    score = 100 * (1 - mdr)
    best = max(post, key=post.get)
    res = ScoreResult(
        score=float(np.median(score)), lo=float(np.percentile(score, 5)), hi=float(np.percentile(score, 95)),
        class_probs={k: round(float(v), 4) for k, v in sorted(post.items(), key=lambda kv: -kv[1])},
        class_map=best, gem_taxonomy=f"{GEM.get(system(best), GEM.get(family(best), '?'))}/HEX:{attrs.storeys}",
        damage={f"pga_{pga:.2f}": dict(zip(DAMAGE_STATES, (round(float(v), 4) for v in probs[j])))
                for j, (pga, _) in enumerate(SCENARIOS)})
    if period is not None:
        res.k_ratio, res.anomaly_z, res.anomaly_flag, _ = stiffness_anomaly(attrs, period)
    return res


def drift_concentration_ratio(floors: np.ndarray, amps: np.ndarray, n_storeys: int) -> float:
    """Measured over reference share of roof displacement reached at the lowest instrumented floor.

    The reference is a regular shear-type first mode, sin(pi z / 2H). A value above 1 means more of
    the deformation happens below the lowest phone than in a regular building (soft lower storeys).
    """
    floors, amps = np.asarray(floors, float), np.asarray(amps, float)
    lo, hi = np.argmin(floors), np.argmax(floors)
    if floors[lo] == floors[hi] or amps[hi] <= 0:
        return 1.0
    ref = np.sin(np.pi * floors / (2 * n_storeys))
    return float((amps[lo] / amps[hi]) / (ref[lo] / ref[hi]))
