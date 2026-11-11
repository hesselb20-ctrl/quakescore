"""Extract the Hazus 6.1 parameter tables from docs/research/codes_and_fragility.md into JSON.

The Markdown file is the transcription of record (with table numbers and source URL). Generating the
JSON from it avoids a second manual transcription.
"""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "docs" / "research" / "codes_and_fragility.md"
OUT = ROOT / "quakescore" / "vuln" / "data" / "hazus61.json"
LEVELS = {"High-Code": "high", "Moderate-Code": "moderate", "Low-Code": "low", "Pre-Code": "pre"}


def num(s: str):
    s = s.strip().replace(",", "")
    return None if s in ("*", "-", "") else float(s)


def main() -> None:
    types: dict[str, dict] = {}
    section = None
    for line in SRC.read_text(encoding="utf-8").splitlines():
        if line.startswith("#"):
            section = None
            if "3a." in line:
                section = "base"
            elif "3.3" in line:
                section = "kappa"
            else:
                for key, lvl in LEVELS.items():
                    if line.startswith(f"#### {key}"):
                        section = lvl
            continue
        if section is None or not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        name = re.sub(r"\s*\(\*\)", "", cells[0])
        if not re.fullmatch(r"[A-Z]+\d?[LMH]?", name) or name in ("Type",):
            continue
        t = types.setdefault(name, {"levels": {}})
        if section == "base":
            t.update(roof_ht_ft=num(cells[4]), Te=num(cells[5]), alpha1=num(cells[6]), alpha2=num(cells[7]),
                     typical_storeys=num(cells[2]))
        elif section == "kappa":
            for lvl, cell in zip(("high", "moderate", "low", "pre"), cells[1:5]):
                t["levels"].setdefault(lvl, {})["kappa"] = [float(v) for v in cell.split("/")]
        else:
            med, beta = zip(*[(float(a), float(b)) for a, b in (c.split("/") for c in cells[7:11])])
            t["levels"].setdefault(section, {}).update(
                Dy=num(cells[3]), Ay=num(cells[4]), Du=num(cells[5]), Au=num(cells[6]),
                median_in=list(med), beta=list(beta), flagged="(*)" in cells[0])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    meta = {"source": "FEMA Hazus Earthquake Model Technical Manual, Hazus 6.1, July 2024",
            "tables": "5-1, 5-8, 5-12 to 5-15, 5-19 to 5-22, 5-42",
            "transcription": "docs/research/codes_and_fragility.md", "units": "inches, g, seconds"}
    OUT.write_text(json.dumps({"meta": meta, "types": types}, indent=1))
    complete = [k for k, v in types.items() if len(v["levels"]) == 4 and all("median_in" in x and "kappa" in x for x in v["levels"].values())]
    print(f"{len(types)} types, {len(complete)} complete: {sorted(complete)}")


if __name__ == "__main__":
    main()
