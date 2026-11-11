"""Milestone 3: compare real-building sessions against published reference values.

Usage: python experiments/m3_validate_real.py <folder of uploaded session JSON files> [reference.csv]

Session files are the upload schema v1 (plain or gzip), exactly as the app writes them. The reference
CSV has columns: building_id, name, storeys, height_m, f1_ref_hz (several values separated by ";"
for the two directions), source. Protocol and candidate buildings: docs/validation_protocol.md.

Nothing is labelled REAL unless it comes out of this script from real session files. With no
sessions the script writes the empty table, which is the current state of the project.
"""
from __future__ import annotations

import csv
import gzip
import json
import pathlib
import sys

import numpy as np

from common import RESULTS, save
from quakescore.artefacts.reject import apply, pick_fundamental
from quakescore.ident.identify import identify
from quakescore.service.codec import decode


def load_sessions(folder: pathlib.Path) -> dict[str, list]:
    out: dict[str, list] = {}
    for path in sorted(folder.glob("*.json*")):
        raw = path.read_bytes()
        payload = json.loads(gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw)
        s = decode(payload)                 # provenance is REAL unless the simulator marked the payload
        out.setdefault(s.building_id, []).append(s)
    return out


def main() -> None:
    folder = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path("data/real_sessions")
    ref_path = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else pathlib.Path("data/reference_buildings.csv")
    refs = list(csv.DictReader(ref_path.open(encoding="utf-8"))) if ref_path.exists() else []
    sessions = load_sessions(folder) if folder.exists() else {}
    rows = []
    for ref in refs:
        sess = sessions.get(ref["building_id"], [])
        f_ref = [float(v) for v in ref["f1_ref_hz"].split(";") if v.strip()]
        row = {"building_id": ref["building_id"], "name": ref["name"], "storeys": ref["storeys"],
               "f1_ref_hz": f_ref, "source": ref["source"], "sessions": len(sess),
               "contributors": len({s.contributor for s in sess}), "phone_models": sorted({s.phone_model for s in sess}),
               "f1_hz": None, "f1_ci": None, "zeta": None, "zeta_ci": None, "error_pct": None, "within_5": None, "within_10": None}
        if sess:
            modes = apply(identify(sess, n_boot=200, rng=np.random.default_rng(0)))
            fund = pick_fundamental(modes, expected_f1=min(f_ref) if f_ref else None)
            if fund is not None:
                nearest = min(f_ref, key=lambda v: abs(fund.f / v - 1)) if f_ref else None
                err = None if nearest is None else 100 * (fund.f / nearest - 1)
                row.update(f1_hz=fund.f, f1_ci=list(fund.f_ci), zeta=fund.zeta, zeta_ci=list(fund.zeta_ci), error_pct=err,
                           within_5=None if err is None else abs(err) <= 5, within_10=None if err is None else abs(err) <= 10)
            row["all_modes"] = [{"f": m.f, "zeta": m.zeta, "z": m.z, "label": m.label} for m in modes]
        rows.append(row)
    measured = [r for r in rows if r["error_pct"] is not None]
    prov = {x.provenance for ss in sessions.values() for x in ss}
    rehearsal = bool(measured) and prov != {"REAL"}
    label = "NONE (no real sessions yet)" if not measured else (
        "SIM (rehearsal with simulated sessions, not a validation)" if rehearsal else "REAL")
    summary = {"provenance": label, "reference_buildings": len(refs),
               "buildings_with_sessions": sum(r["sessions"] > 0 for r in rows), "buildings_identified": len(measured),
               "within_5pct": sum(bool(r["within_5"]) for r in measured), "within_10pct": sum(bool(r["within_10"]) for r in measured)}
    save("m3/rehearsal_sim.json" if rehearsal else "m3/real_building_validation.json", {"summary": summary, "rows": rows})
    lines = ["# Milestone 3: real-building validation\n", f"Provenance: **{summary['provenance']}**\n",
             "| Building | Storeys | Reference f1 (Hz) | Sessions | Phones | Measured f1 (Hz) | 90% interval | Error | Damping (90% interval) |",
             "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        f1 = "-" if r["f1_hz"] is None else f"{r['f1_hz']:.3f}"
        ci = "-" if r["f1_ci"] is None else f"{r['f1_ci'][0]:.3f} to {r['f1_ci'][1]:.3f}"
        er = "-" if r["error_pct"] is None else f"{r['error_pct']:+.1f}%"
        zt = "-" if r["zeta"] is None else f"{100 * r['zeta']:.1f}% ({100 * r['zeta_ci'][0]:.1f} to {100 * r['zeta_ci'][1]:.1f})"
        lines.append(f"| {r['name']} | {r['storeys']} | {', '.join(f'{v:g}' for v in r['f1_ref_hz'])} | {r['sessions']} | "
                     f"{len(r['phone_models'])} | {f1} | {ci} | {er} | {zt} |")
    if not rows:
        lines.append("| (no reference file) | | | | | | | | |")
    lines.append(f"\nBuildings within 5%: {summary['within_5pct']} of {len(measured)} measured. Target: at least 5 buildings, 3 to 30+ storeys.")
    (RESULTS / ("m3_rehearsal_sim.md" if rehearsal else "m3_summary.md")).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
