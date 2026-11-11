"""Hazus-style capacity spectrum method and structural fragility, adjusted by measured parameters.

Class parameters are Hazus 6.1 (REF, see data/hazus61.json). The adjustments for measured period,
drift concentration and damping are physics-based and have not been calibrated against observed
damage (label: ASSUMED until validated).
"""
from __future__ import annotations

import json
import pathlib
from functools import lru_cache

import numpy as np
from scipy.stats import norm

G_IN = 386.09                                        # g in inch/s^2
DAMAGE_STATES = ("slight", "moderate", "extensive", "complete")
# structural repair cost per state relative to the complete state (Hazus 6.1 Table 11-2, normalised)
DAMAGE_FACTOR = np.array([0.02, 0.10, 0.50, 1.00])
SCENARIOS = ((0.15, 0.3), (0.30, 0.4), (0.60, 0.3))  # (PGA in g, weight in the score)
# elastic damping in percent by material family (ASSUMED; Hazus bases its values on Newmark and Hall)
ELASTIC_DAMPING = {"W": 10.0, "S": 5.0, "C": 7.0, "PC": 7.0, "RM": 7.0, "URM": 10.0}
HEIGHT_EXPONENT = {"S1": 0.8, "C1": 0.9}             # code period-height exponent, 0.75 otherwise


@lru_cache(maxsize=1)
def tables() -> dict:
    path = pathlib.Path(__file__).parent / "data" / "hazus61.json"
    return json.loads(path.read_text())["types"]


def family(btype: str) -> str:
    for key in ("URM", "PC", "RM", "W", "S", "C"):
        if btype.startswith(key):
            return key
    raise KeyError(btype)


def system(btype: str) -> str:
    return btype[:-1] if btype[-1] in "LMH" and len(btype) > 2 else btype


def capacity(sd: np.ndarray, dy: float, ay: float, du: float, au: float) -> np.ndarray:
    """Hazus capacity curve: linear to yield, elliptical transition, plateau at ultimate. Sa in g."""
    k = ay / dy
    x = dy - du
    c = (ay**2 - x * k * ay - au**2) / (2 * (ay - au) - x * k)
    b = au - c
    a2 = -x * b * b / ((ay - c) * k)
    ell = c + b * np.sqrt(np.clip(1 - (sd - du) ** 2 / a2, 0, None))
    return np.where(sd <= dy, k * sd, np.where(sd >= du, au, ell))


def spectrum(t: np.ndarray, pga: float, tc: float = 0.5, tb: float = 0.1, tl: float = 4.0):
    """Standard 5%-damped shape: plateau 2.5 PGA, constant velocity beyond tc. Returns (Sa, region)."""
    t = np.maximum(t, 1e-3)
    plateau = 2.5 * pga
    sa = np.where(t < tb, pga * (1 + 1.5 * t / tb), np.where(t <= tc, plateau, np.where(
        t <= tl, plateau * tc / t, plateau * tc * tl / t**2)))
    return sa, t > tc


def performance_point(dy: float, ay: float, du: float, au: float, pga: float, b_el: float,
                      kappa: float) -> float:
    """Spectral displacement (inches) where capacity meets the damping-reduced demand."""
    sd = np.geomspace(1e-3, 400.0, 500)
    sa = capacity(sd, dy, ay, du, au)
    t_eff = 2 * np.pi * np.sqrt(sd / (sa * G_IN))
    hyst = 63.7 * kappa * np.clip((ay * sd - dy * sa) / (sa * sd), 0, None)
    b_eff = np.clip(b_el + hyst, 2.0, 45.0)
    ra = 2.12 / (3.21 - 0.68 * np.log(b_eff))
    rv = 1.65 / (2.31 - 0.41 * np.log(b_eff))
    sa5, velocity = spectrum(t_eff, pga)
    gap = sa5 / np.where(velocity, rv, ra) - sa
    below = np.flatnonzero(gap < 0)
    if len(below) == 0:
        return float(sd[-1])
    i = below[0]
    if i == 0:
        return float(sd[0])
    w = gap[i - 1] / (gap[i - 1] - gap[i])
    return float(np.exp(np.log(sd[i - 1]) + w * (np.log(sd[i]) - np.log(sd[i - 1]))))


def building_parameters(btype: str, level: str, height_m: float, t_ratio: float = 1.0,
                        dcf_ratio: float = 1.0, damping_ratio: float = 1.0) -> dict:
    """Class parameters scaled to this building.

    t_ratio      measured period / expected period for the class (1 = as expected)
    dcf_ratio    measured / class drift concentration (above 1 = drift concentrated low down)
    damping_ratio  measured / expected ambient damping; enters elastic damping with exponent 0.5
    """
    t = tables()[btype]
    lv = t["levels"][level]
    scale = (height_m / 0.3048) / t["roof_ht_ft"]
    te = t["Te"] * scale ** HEIGHT_EXPONENT.get(system(btype), 0.75) * t_ratio
    dy = G_IN / (4 * np.pi**2) * lv["Ay"] * te**2
    return {
        "te": te, "dy": dy, "ay": lv["Ay"], "du": dy * lv["Du"] / lv["Dy"], "au": lv["Au"],
        "median": np.array(lv["median_in"]) * scale / dcf_ratio, "beta": np.array(lv["beta"]),
        "b_el": ELASTIC_DAMPING[family(btype)] * damping_ratio**0.5, "kappa": lv["kappa"][1],
    }


def damage_probabilities(p: dict, pga: float) -> np.ndarray:
    """Probability of being in each of slight, moderate, extensive, complete (exclusive states)."""
    sd = performance_point(p["dy"], p["ay"], p["du"], p["au"], pga, p["b_el"], p["kappa"])
    exceed = norm.cdf(np.log(sd / p["median"]) / p["beta"])
    exceed = np.minimum.accumulate(exceed)
    return np.append(exceed[:-1] - exceed[1:], exceed[-1])


def mean_damage_ratio(btype: str, level: str, height_m: float, **adjust) -> tuple[float, np.ndarray]:
    """Scenario-weighted structural mean damage ratio and the per-scenario state probabilities."""
    p = building_parameters(btype, level, height_m, **adjust)
    probs = np.stack([damage_probabilities(p, pga) for pga, _ in SCENARIOS])
    weights = np.array([w for _, w in SCENARIOS])
    return float(weights @ (probs @ DAMAGE_FACTOR)), probs
