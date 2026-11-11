"""Sample portfolio report from the demo city records (SIM). Writes a CSV input, the report and a summary.

The input is what an insurer would upload (coordinates here; addresses work the same way through the
API). Matching is done with the service's portfolio matcher so the sample exercises the real code.
"""
from __future__ import annotations

import csv
import io
import json

import numpy as np

from common import RESULTS, ROOT, save

N = 40


def main() -> None:
    recs = json.loads((RESULTS / "demo_city" / "buildings.json").read_text())
    rng = np.random.default_rng(11)
    with_storeys = [r for r in recs if r["attrs"]["storeys"] and r["attrs"]["storeys"] >= 4]
    pick = [with_storeys[i] for i in sorted(rng.choice(len(with_storeys), min(N, len(with_storeys)), replace=False))]
    buf = io.StringIO()
    wr = csv.writer(buf)
    wr.writerow(["policy_ref", "lat", "lon"])
    for i, r in enumerate(pick):
        wr.writerow([f"P-{1000 + i}", f"{r['attrs']['lat']:.6f}", f"{r['attrs']['lon']:.6f}"])
    (RESULTS / "demo_city" / "sample_portfolio_input.csv").write_text(buf.getvalue())

    rows = []
    for i, r in enumerate(pick):
        sc, cov = r["score"], r["coverage"]
        rows.append({
            "policy_ref": f"P-{1000 + i}", "building_id": r["building_id"],
            "name": r["attrs"]["name"] or r["attrs"]["address"] or r["building_id"],
            "storeys": r["attrs"]["storeys"], "status": cov["status"], "sessions": cov["sessions"],
            "contributors": cov["contributors"],
            "score": None if sc is None else sc["value"], "lo": None if sc is None else sc["lo"], "hi": None if sc is None else sc["hi"],
            "class_only": (r.get("prior") or {}).get("value") if sc is None else sc["prior_value"],
            "f1": r["f1"], "k_ratio": None if r["stiffness"] is None else r["stiffness"]["k_ratio"],
            "flag": bool(r["stiffness"] and r["stiffness"]["flag"]), "drift_alert": bool(r["drift"] and r["drift"]["alert"]),
            "class": r["class_map"]})
    scored = [x for x in rows if x["status"] == "scored"]
    summary = {"provenance": "SIM", "rows": len(rows), "matched": len(rows), "scored": len(scored),
               "coverage_pct": round(100 * len(scored) / len(rows), 1),
               "score_median": float(np.median([x["score"] for x in scored])) if scored else None,
               "score_p10": float(np.percentile([x["score"] for x in scored], 10)) if scored else None,
               "band_width_median": float(np.median([x["hi"] - x["lo"] for x in scored])) if scored else None,
               "stiffness_flags": sum(x["flag"] for x in rows), "drift_alerts": sum(x["drift_alert"] for x in rows)}
    save("demo_city/sample_portfolio.json", {"summary": summary, "rows": rows})
    # Names and addresses are left out of the printed sample on purpose: the scores are simulated and
    # must not be read as assessments of the real buildings at those footprints.
    L = ["| Ref | Storeys | Status | Sessions | QuakeScore (5-95%) | Class only | f1 (Hz) | Stiffness vs class | Alerts |",
         "|---|---|---|---|---|---|---|---|---|"]
    show = scored[:9] + [x for x in rows if x["status"] != "scored"][:3]
    for x in show:
        score = "not released" if x["score"] is None else f"**{x['score']:.0f}** ({x['lo']:.0f}-{x['hi']:.0f})"
        k = "-" if x["k_ratio"] is None else f"{100 * x['k_ratio']:.0f}%"
        alerts = ", ".join(a for a, on in (("soft for class", x["flag"]), ("frequency drop", x["drift_alert"])) if on) or "-"
        co = "-" if x["class_only"] is None else f"{x['class_only']:.0f}"
        f1 = "-" if x["f1"] is None else f"{x['f1']:.2f}"
        L.append(f"| {x['policy_ref']} | {x['storeys']} | {x['status'].replace('_', ' ')} | {x['sessions']} | {score} | {co} | {f1} | {k} | {alerts} |")
    L.append("")
    L.append(f"Portfolio of {summary['rows']} locations of four storeys or more: {summary['scored']} scored ({summary['coverage_pct']:.0f}% coverage), "
             f"median score {summary['score_median']:.0f}, lowest decile below {summary['score_p10']:.0f}, median band width "
             f"{summary['band_width_median']:.0f} points, {summary['stiffness_flags']} stiffness flags, {summary['drift_alerts']} frequency-drop alerts. "
             "Twelve rows shown; addresses withheld because the scores are simulated.")
    (RESULTS / "demo_city" / "sample_portfolio.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
