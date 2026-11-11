"""Write results/m4_summary.md, m5_summary.md, m6_summary.md and demo_city_summary.md from the JSON outputs."""
from __future__ import annotations

from common import RESULTS, load


def pct(v, d=0):
    return "n/a" if v is None else f"{100 * v:.{d}f}%"


def m4() -> None:
    tune = load("m4/artefact_rejection.json")
    try:
        r = load("m4/artefact_rejection_test.json")
    except FileNotFoundError:
        r = tune
    c, k, pub, fu = r["candidates"], r["accepted"], r["published"], r["fundamental"]
    L = ["# Milestone 4 results: artefact rejection\n",
         "Provenance: **SIM** (time-domain simulation with interference). Thresholds were set on this kind of",
         "data and have to be re-tuned on labelled real sessions.\n",
         f"Set: {r['buildings']} buildings, {r['sessions']} sessions of {r['hours_per_session']:g} h, three phone models (one with a",
         "self-noise resonance and a 1 Hz tick), persistent HVAC tones and elevator rumble per building, per-night",
         "appliances, mains aliases and footsteps, 25% soft surfaces, calm and windy nights mixed.",
         f"Windows kept by the stationarity gate: {pct(r['mean_window_accept_fraction'], 1)}.\n",
         ("**This is the held-out test set.** Thresholds were set on a separate tuning set of the same size and then frozen; "
          f"on the tuning set, with the thresholds as they stood before the last adjustment, the published non-structural share was "
          f"{pct(tune['published_false_share'], 1)}.\n") if r is not tune else "**Tuning set only; no held-out evaluation yet.**\n",
         "Labels: structural = within 2% of a true mode and not on an injected interference frequency;",
         "non-structural = on an interference frequency, or more than 4% from every true mode; ambiguous = near",
         "both, or 2-4% from a true mode. Ambiguous peaks are excluded from the rates.\n",
         "| | Candidates (z >= 6) | Accepted as structural |", "|---|---|---|",
         f"| Structural | {c['structural']} | {k['structural']} |",
         f"| Non-structural | {c['non-structural']} | {k['non-structural']} |",
         f"| Ambiguous | {c['ambiguous']} | {k['ambiguous']} |",
         f"| Share non-structural (ambiguous excluded) | {pct(r['false_share_before'], 1)} | **{pct(r['false_share_after'], 1)}** |",
         "",
         f"Structural candidates kept: {pct(r['structural_retention'], 1)}.\n",
         "## What the product would publish\n",
         "The lowest three accepted modes inside the plausibility window for the building's height:\n",
         "| Structural | Non-structural | Ambiguous | Share non-structural |", "|---|---|---|---|",
         f"| {pub['structural']} | {pub['non-structural']} | {pub['ambiguous']} | **{pct(r['published_false_share'], 1)}** |",
         "",
         f"Fundamental: the true first mode was among the candidates in {fu['first_mode_detected']} of {fu['buildings']} buildings. A fundamental",
         f"was reported for {fu['reported']} buildings: {fu['reported_correct']} correct (a true first mode in either direction),",
         f"{fu['reported_wrong']} wrong.\n",
         "## Non-structural peaks by source\n", "| Source | Candidates | Passed rejection |", "|---|---|---|"]
    for key, v in sorted(r["false_by_source"].items(), key=lambda kv: -kv[1]["candidates"]):
        L.append(f"| {key} | {v['candidates']} | {v['passed']} |")
    L += ["", "## Labels assigned\n", "| Truth: label | Count |", "|---|---|"]
    for key, v in sorted(r["label_counts"].items(), key=lambda kv: -kv[1]):
        L.append(f"| {key} | {v} |")
    L += ["", f"Fleet registry (frequencies one phone model reports across unrelated buildings): `{r['registry']}`", ""]
    (RESULTS / "m4_summary.md").write_text("\n".join(L), encoding="utf-8")


def m5() -> None:
    r = load("m5/vulnerability.json")
    L = ["# Milestone 5 results: vulnerability model\n",
         "Class parameters: **REF** (Hazus 6.1). Adjustments for measured period, drift concentration and damping:",
         "**ASSUMED** physics, not calibrated against observed damage. Experiments: **SIM**.\n",
         "QuakeScore = 100 x (1 - scenario-weighted structural mean damage ratio); scenarios PGA 0.15, 0.30, 0.60 g",
         "with weights 0.3, 0.4, 0.3; 100 is least vulnerable.\n",
         "## 1. Class baseline at typical height (no measurement)\n",
         "| Type | Height (m) | Te (s) | High-code | Moderate | Low | Pre-code |", "|---|---|---|---|---|---|---|"]
    for b in r["baseline"]:
        L.append(f"| {b['type']} | {b['height_m']} | {b['Te']} | {b['high']} | {b['moderate']} | {b['low']} | {b['pre']} |")
    L += ["", "## 2. Sensitivity of the score to measured quantities\n"]
    for key, s in r["sensitivity"].items():
        L += [f"**{key}**\n", "| Stiffness ratio | " + " | ".join(s["stiffness_ratio"]) + " |", "|---|" + "---|" * len(s["stiffness_ratio"]),
              "| Score | " + " | ".join(str(v) for v in s["stiffness_ratio"].values()) + " |", "",
              "| Drift concentration ratio | " + " | ".join(s["drift_concentration"]) + " |", "|---|" + "---|" * len(s["drift_concentration"]),
              "| Score | " + " | ".join(str(v) for v in s["drift_concentration"].values()) + " |", "",
              "| Damping ratio (measured / expected) | " + " | ".join(s["damping_ratio"]) + " |", "|---|" + "---|" * len(s["damping_ratio"]),
              "| Score | " + " | ".join(str(v) for v in s["damping_ratio"].values()) + " |", ""]
    bn = r["band_narrowing"]
    L += ["## 3. What a measured period adds\n",
          f"Over {bn['buildings']} random buildings: median width of the 5-95% score band is {bn['prior_band_width_median']:.1f} points from public",
          f"attributes alone and {bn['measured_band_width_median']:.1f} points with a measured first-mode period. The score moves by a median of",
          f"{bn['abs_score_shift_median']:.1f} points and by more than {bn['abs_score_shift_p90']:.1f} points for one building in ten.\n",
          "## 4. Stiffness-anomaly detector, height known only\n",
          "A flag is raised when the building is more than 2 sigma softer than every plausible class.\n",
          "| True stiffness relative to class | Flagged | Median z under the most probable class |", "|---|---|---|"]
    for k, v in r["anomaly_power"].items():
        name = "as expected (false-flag rate)" if k == "1.0" else f"{100 * (1 - float(k)):.0f}% softer"
        L.append(f"| {name} | {pct(v['flag_rate'], 1)} | {v['median_z_map_class']:+.2f} |")
    L += ["", "With height alone, class scatter (sigma of ln T = 0.25) hides all but gross anomalies: a building 30% softer",
          "than expected is flagged about 4% of the time. The detector needs better covariates (plan dimensions, wall",
          "density, known system) to become useful; tracking a building against itself over time is far more sensitive",
          "(Milestone 6).\n",
          "## 5. Soft-storey indicator from mode shapes\n",
          "Five nights of synchronised frames, phones spread over the height, first storey at 30% of regular stiffness.",
          "Indicator: share of roof displacement reached at the lowest phone, relative to a regular reference shape.\n",
          "| Storeys | Phones | Nights | Regular (median) | Soft storey (median) | Detected at 5% false alarms |", "|---|---|---|---|---|---|"]
    for s in r["soft_storey"]:
        L.append(f"| {s['storeys']} | {s['phones']} | {s['env']} | {s['regular_median']:.2f} | {s['soft_median']:.2f} | {pct(s['detection_rate'])} |")
    L += ["", "## 6. Validation against observed damage\n",
          "Not done. No open dataset pairs a pre-earthquake modal measurement with a post-earthquake damage grade for",
          "the same building, so the measured-period adjustment cannot be tested building by building. What is possible",
          "next: a class-level comparison against the ACI 133 Turkey 2023 reinforced-concrete database (about 240",
          "buildings with storeys, height and damage grade, CC BY 4.0), and expert ratings on a test set. See",
          "docs/references.md and docs/REPORT.md.", ""]
    (RESULTS / "m5_summary.md").write_text("\n".join(L), encoding="utf-8")


def m6() -> None:
    r = load("m6/change_detection.json")
    a = r["assumptions"]
    L = ["# Milestone 6 results: change detection\n", "Provenance: **SIM** (fast path).\n",
         f"One year of sessions in epochs of {a['epoch_sessions']} nights. Frequency follows temperature ({100 * a['temp_coeff_per_C']:.2f}% per degree C,",
         f"assumed) and an unobserved slow term ({100 * a['slow_sigma']:.1f}% RMS, assumed). A permanent stiffness loss is applied half-way.",
         "Half the nights are calm, so many epochs give no estimate. Threshold set for 5% false alarms on loss-free runs.\n",
         "| Storeys | Phone | Sessions in the year | Epochs with an estimate | Residual scatter | 2.5% loss | 5% loss | 10% loss | 20% loss | Minimum detectable loss (90%) |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for s in r["summary"]:
        d = s["detect"]
        md = "not reached" if s["min_detectable_loss"] is None else f"{100 * s['min_detectable_loss']:g}%"
        L.append(f"| {s['storeys']} | {s['phone']} | {s['sessions_total']} | {pct(s['usable_epoch_share'])} | {s['resid_sigma_pct']:.2f}% | "
                 f"{pct(d['0.025'])} | {pct(d['0.05'])} | {pct(d['0.1'])} | {pct(d['0.2'])} | {md} |")
    L += ["", "A stiffness loss of 5%, 10% and 20% lowers frequency by 2.5%, 5.1% and 10.6%. Estimated step sizes (median, percent of frequency):\n",
          "| Storeys | Phone | Sessions | 2.5% loss | 5% loss | 10% loss | 20% loss |", "|---|---|---|---|---|---|---|"]
    for s in r["summary"]:
        e = s["step_est_pct"]
        L.append(f"| {s['storeys']} | {s['phone']} | {s['sessions_total']} | {e['0.025']:+.2f} | {e['0.05']:+.2f} | {e['0.1']:+.2f} | {e['0.2']:+.2f} |")
    L.append("")
    (RESULTS / "m6_summary.md").write_text("\n".join(L), encoding="utf-8")


def city() -> None:
    s = load("demo_city/summary.json")
    L = ["# Demo city summary\n",
         "Footprints and tags: **REAL** (OpenStreetMap contributors, ODbL), downtown San Francisco.",
         "Structures, contributors, sessions, scores, anomalies and drift: **SIM**. No real session has been contributed.\n",
         "Simulated scores attached to real footprints must never be presented as assessments of those buildings.",
         "Footprints with neither a level count nor a height tag (95 of 687) were treated as single-storey.\n",
         f"Footprints: {s['footprints']} ({s['with_storeys']} with a storey count). Simulated sessions: {s['sessions_total']}.\n",
         "| Status | Buildings |", "|---|---|"]
    L += [f"| {k} | {v} |" for k, v in s["status"].items()]
    L += ["", "| Storeys | Footprints | With at least one session | Scored |", "|---|---|---|---|"]
    L += [f"| {k} | {v['buildings']} | {v['with_sessions']} | {v['scored']} |" for k, v in s["by_storeys"].items()]
    L += ["", "Against the simulated truth (scored buildings only):\n",
          f"- First-mode frequency: median absolute error {pct(s['f1_abs_error_median'], 2)}, 90th percentile {pct(s['f1_abs_error_p90'], 2)},",
          f"  within 5% in {pct(s['f1_within_5pct'], 1)} of buildings; wrong mode picked in {s['f1_wrong_mode']}.",
          f"- Stiffness anomalies: {s['anomalous_buildings']} planted, {s['anomalous_scored']} of them scored, {s['anomaly_flags']} flags raised,",
          f"  {s['anomaly_flags_correct']} correct.",
          f"- Simulated damage: {s['damaged_scored']} scored buildings lost 12% stiffness; {s['drift_alerts']} drift alerts, {s['drift_alerts_correct']} correct.",
          f"- Score: median {s['score_median']}, median band width {s['score_band_median_width']:.1f} points (class-based prior: {s['prior_band_median_width']:.1f}).",
          ""]
    (RESULTS / "demo_city_summary.md").write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    import sys
    for name in sys.argv[1:] or ["m4", "m5", "m6", "city"]:
        try:
            globals()[name]()
            print("wrote", name)
        except FileNotFoundError as e:
            print("skipped", name, e)
