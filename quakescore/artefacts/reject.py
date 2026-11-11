"""Reject non-structural peaks: machinery tones, bursts, furniture, phone-model artefacts.

Each candidate mode carries the features computed in ident.identify.peak_features. A candidate is
labelled "structural" only if it passes every test; otherwise the label names the first failed test.
Thresholds are provisional (label: ASSUMED) and were set on simulated contaminated sessions; they
have to be re-tuned on labelled real sessions.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..ident.identify import Mode, identify


@dataclass(frozen=True)
class RejectConfig:
    zeta_min: float = 0.003          # narrower than any building: rotating machinery, aliases
    zeta_max: float = 0.08           # broader than any building at ambient level: furniture, mounts
    tone_min: float = 0.75           # normalised periodogram variance; a steady sinusoid tends to 0
    burst_max: float = 1.5           # well above 1: energy arrives in bursts (elevator runs, appliances)
    # A lateral mode has no vertical motion; floor-borne machinery does. Reject a peak that is also
    # present, at this share of its horizontal power, on the vertical axis.
    vertical_ratio_max: float = 0.10
    vertical_z_min: float = 4.0
    # Share of the peak carried by the single strongest session. A structural mode is legitimately
    # much stronger on windy nights, so only a peak that lives in one session is rejected.
    top1_share_max: float = 0.7
    min_sessions_persistence: int = 6
    support_z_min: float = 3.0       # pooled per-session amplitude at the peak, in sigma
    z_release: float = 7.0           # detection score needed on its own
    z_release_shared: float = 6.0    # ... or this, if at least two contributors see the peak
    boot_min: float = 0.6
    model_z_hit: float = 4.0         # one phone model sees the peak at this many sigma ...
    # ... while the other models, with enough sessions, exclude this share of its absolute power. The
    # share is small on purpose: excitation differs by one to two orders of magnitude between calm and
    # windy nights, and a contributor's nights are not a random sample. The fleet check is the main
    # defence against phone artefacts; this rule only catches gross cases inside one building.
    model_amp_share: float = 0.02
    model_min_rest_sessions: int = 5
    fleet_tol: float = 0.015
    plaus_lo: float = 1 / 3.5        # fundamental frequency window relative to the height-based
    plaus_hi: float = 3.5            # expectation; deliberately wide so soft buildings survive


def classify(m: Mode, cfg: RejectConfig = RejectConfig(),
             registry: dict[str, list[float]] | None = None) -> str:
    """Return "structural" or "rejected:<reason>" for one candidate."""
    ft = m.features
    if m.zeta < cfg.zeta_min:                        # narrower than any building: a line
        return "rejected:too-narrow"
    if m.zeta > cfg.zeta_max:
        return "rejected:too-broad"
    if ft.get("support_z", np.inf) < cfg.support_z_min:   # the sessions themselves do not show the bump
        return "rejected:unsupported"
    if ft.get("tone", 1.0) < cfg.tone_min:
        return "rejected:tone"
    if ft.get("tone", 1.0) > cfg.burst_max:
        return "rejected:bursty"
    if ft.get("vertical_z", 0.0) > cfg.vertical_z_min and ft.get("vertical_ratio", 0.0) > cfg.vertical_ratio_max:
        return "rejected:vertical"
    if m.n_sessions >= cfg.min_sessions_persistence and ft.get("top1_share", 0.0) > cfg.top1_share_max:
        return "rejected:single-session"
    mz = ft.get("model_z", {})
    ma = ft.get("model_amp", {})
    if len(ma) >= 2:
        # A structural mode has the same absolute power in every phone (up to mode-shape factors).
        # A phone artefact exists in one model only. Compare absolute power, not detection scores,
        # because a quiet phone always scores higher than a noisy one on the same signal.
        top = max(ma, key=lambda k: ma[k][0])
        a_top, s_top = ma[top]
        wv = np.array([1 / ma[k][1] ** 2 for k in ma if k != top])
        av = np.array([ma[k][0] for k in ma if k != top])
        a_rest, s_rest = float((wv * av).sum() / wv.sum()), float(1 / np.sqrt(wv.sum()))
        n_rest = m.n_sessions - ft.get("model_sessions", {}).get(top, 0)
        if (n_rest >= cfg.model_min_rest_sessions and a_top > cfg.model_z_hit * s_top
                and a_rest + 3 * s_rest < cfg.model_amp_share * a_top):
            return "rejected:phone-model"
    if registry:
        for model in mz:
            if any(abs(m.f / fa - 1) < cfg.fleet_tol for fa in registry.get(model, [])):
                if len(mz) == 1 or mz[model] == max(mz.values()):
                    return "rejected:phone-model-fleet"
    if np.isfinite(m.boot_ok) and m.boot_ok < cfg.boot_min:
        return "rejected:unstable"
    if not (m.z >= cfg.z_release or (m.z >= cfg.z_release_shared and ft.get("n_contrib_seen", 0) >= 2)):
        return "rejected:weak"
    return "structural"


def apply(modes: list[Mode], cfg: RejectConfig = RejectConfig(),
          registry: dict[str, list[float]] | None = None) -> list[Mode]:
    for m in modes:
        m.label = classify(m, cfg, registry)
    return modes


def pick_fundamental(modes: list[Mode], expected_f1: float | None = None,
                     cfg: RejectConfig = RejectConfig()) -> Mode | None:
    """Lowest structural mode inside the plausibility window for the building's height."""
    ok = [m for m in modes if m.label == "structural"]
    if expected_f1 is not None:
        ok = [m for m in ok if cfg.plaus_lo * expected_f1 <= m.f <= cfg.plaus_hi * expected_f1]
    return min(ok, key=lambda m: m.f) if ok else None


def model_peaks(sessions: list, z_min: float = 6.0) -> dict[str, list[float]]:
    """Peaks found in one building using one phone model's sessions at a time."""
    out: dict[str, list[float]] = {}
    for model in {s.phone_model for s in sessions}:
        sub = [s for s in sessions if s.phone_model == model]
        if len(sub) >= 2:
            out[model] = [m.f for m in identify(sub, z_min=z_min, n_boot=0)]
    return out


def registry_from_peaks(per_building: list[dict[str, list[float]]], min_buildings: int = 3,
                        min_share: float = 0.3, tol: float = 0.015) -> dict[str, list[float]]:
    """Fleet check: frequencies that one phone model reports in many unrelated buildings.

    A frequency that recurs (within tol) in at least min_buildings buildings and min_share of the
    buildings where the model is present cannot be structural, because buildings do not share modes.
    """
    per_model: dict[str, list[list[float]]] = {}
    for d in per_building:
        for model, fl in d.items():
            per_model.setdefault(model, []).append(fl)
    registry: dict[str, list[float]] = {}
    for model, lists in per_model.items():
        out: list[float] = []
        for f in sorted(f for fl in lists for f in fl):
            if any(abs(f / o - 1) < tol for o in out):
                continue
            hits = sum(1 for fl in lists if any(abs(g / f - 1) < tol for g in fl))
            if hits >= min_buildings and hits >= min_share * len(lists):
                out.append(float(np.median([g for fl in lists for g in fl if abs(g / f - 1) < tol])))
        registry[model] = out
    return registry


def build_registry(sessions_by_building: dict[str, list], **kw) -> dict[str, list[float]]:
    """Convenience wrapper: per-building peaks, then the fleet registry."""
    return registry_from_peaks([model_peaks(s) for s in sessions_by_building.values()], **kw)
