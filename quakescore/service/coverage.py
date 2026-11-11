"""Coverage engine and K-threshold gate.

Every read path (API, static export, portfolio) goes through `building_view`, which is the only
function that decides what may leave the service:

  released  <=>  record exists
                 and record.coverage.contributors >= K_c and record.coverage.sessions >= K_s
                 and record.coverage.status == "scored"
                 and the record has a score with a complete band (value, lo, hi)

A released view carries the modal parameters, score (always with its band), class, stiffness,
damage, drift and spectrum, plus "provenance". A view that is not released carries coverage only:
no modes, no f1, no score, no class, no damage, no drift, no spectrum.

Coverage counts are the larger of the batch record's counts and the live sessions table, because
uploads may arrive after the last batch run. The gate itself uses the record's own counts, since
those are the sessions its parameters were computed from.
"""
from __future__ import annotations

from quakescore.service.config import Config

STATUSES = ("scored", "needs_data", "no_data")
PROVENANCES = ("SIM", "REAL", "FIXTURE")
RELEASED_FIELDS = ("modes", "f1", "f1_lo", "f1_hi", "zeta1", "zeta1_lo", "zeta1_hi", "class_probs",
                   "class_map", "gem_taxonomy", "stiffness", "score", "damage", "drift", "spectrum")
PUBLIC_ATTRS = ("storeys", "height_m", "year", "material", "use", "name", "address")

CAVEAT = ("This is a statistical screening result estimated from phone vibration measurements and "
          "public building data. It is not a structural engineering assessment and must not be used "
          "as one. Only a licensed structural engineer who inspects the building can assess its "
          "safety.")


class RecordError(ValueError):
    pass


def _band_ok(d: dict | None, keys=("value", "lo", "hi")) -> bool:
    if not isinstance(d, dict):
        return False
    try:
        v, lo, hi = (float(d[k]) for k in keys)
    except (KeyError, TypeError, ValueError):
        return False
    return lo <= v <= hi


def validate_record(rec: dict) -> dict:
    """Check a batch result record against the schema in docs/api.md. Raises RecordError."""
    if not isinstance(rec, dict):
        raise RecordError("record must be an object")
    for k in ("building_id", "provenance", "updated", "attrs", "coverage"):
        if k not in rec:
            raise RecordError(f"{rec.get('building_id', '?')}: missing {k}")
    bid = rec["building_id"]
    if rec["provenance"] not in PROVENANCES:
        raise RecordError(f"{bid}: provenance must be one of {PROVENANCES}")
    cov = rec["coverage"]
    for k in ("sessions", "contributors", "floors", "status"):
        if k not in cov:
            raise RecordError(f"{bid}: coverage.{k} missing")
    if cov["status"] not in STATUSES:
        raise RecordError(f"{bid}: coverage.status must be one of {STATUSES}")
    a = rec["attrs"]
    for k in ("lat", "lon"):
        if not isinstance(a.get(k), (int, float)):
            raise RecordError(f"{bid}: attrs.{k} must be a number")
    s = rec.get("score")
    if s is not None:
        if not _band_ok(s):
            raise RecordError(f"{bid}: score needs lo <= value <= hi")
        if not all(0 <= float(s[k]) <= 100 for k in ("value", "lo", "hi")):
            raise RecordError(f"{bid}: score must be within 0-100")
    if rec.get("f1") is not None and not _band_ok(
            {"value": rec["f1"], "lo": rec.get("f1_lo"), "hi": rec.get("f1_hi")}):
        raise RecordError(f"{bid}: f1 needs f1_lo <= f1 <= f1_hi")
    for m in rec.get("modes") or []:
        if not _band_ok({"value": m.get("f"), "lo": m.get("f_lo"), "hi": m.get("f_hi")}):
            raise RecordError(f"{bid}: every mode needs f_lo <= f <= f_hi")
    return rec


def live_cov(rows: list[dict]) -> dict:
    return {"sessions": len(rows), "contributors": len({r["contributor"] for r in rows}),
            "floors": len({r["floor"] for r in rows if r.get("floor") is not None})}


def _needed(sessions: int, contributors: int, cfg: Config) -> tuple[int, int]:
    """Sessions and contributors still needed to reach the K-threshold.
    Each new contributor brings at least one session, hence the max()."""
    c_need = max(cfg.k_contributors - contributors, 0)
    s_need = max(cfg.k_sessions - sessions, c_need)
    return s_need, c_need


def is_released(rec: dict | None, cfg: Config) -> bool:
    if not rec:
        return False
    cov = rec.get("coverage") or {}
    return (cov.get("status") == "scored"
            and int(cov.get("contributors", 0)) >= cfg.k_contributors
            and int(cov.get("sessions", 0)) >= cfg.k_sessions
            and _band_ok(rec.get("score")))


def building_view(b: dict | None, rec: dict | None, live: dict | None, cfg: Config,
                  stale: bool = False) -> dict:
    """The single gate. `b` is the buildings row (may be None if only a record exists).

    `stale` means sessions were deleted after the record was computed: the record's own counts
    can no longer be trusted, so coverage and the K-threshold use the live session table only
    (the record is still released if the remaining live sessions meet K; otherwise withheld).
    """
    live = live or {"sessions": 0, "contributors": 0, "floors": 0}
    rc = (rec or {}).get("coverage") or {}
    if stale:
        sessions, contributors, floors = live["sessions"], live["contributors"], live["floors"]
    else:
        sessions = max(int(rc.get("sessions", 0)), live["sessions"])
        contributors = max(int(rc.get("contributors", 0)), live["contributors"])
        floors = max(int(rc.get("floors", 0)), live["floors"])
    released = is_released(rec, cfg) and (
        not stale or (contributors >= cfg.k_contributors and sessions >= cfg.k_sessions))
    if released:
        status = "scored"
        s_need, c_need = 0, 0
    elif sessions == 0:
        status = "no_data"
        s_need, c_need = _needed(0, 0, cfg)
    else:
        status = "needs_data"
        s_need, c_need = _needed(sessions, contributors, cfg)
        if s_need == 0 and rc.get("sessions_needed"):
            s_need = int(rc["sessions_needed"])   # above K but not yet identifiable
    attrs = dict((rec or {}).get("attrs") or {})
    if b:
        for k, v in (b.get("attrs") or {}).items():
            if k in PUBLIC_ATTRS and attrs.get(k) is None:
                attrs[k] = v
        attrs["lat"], attrs["lon"] = b["lat"], b["lon"]
    attrs = {k: attrs.get(k) for k in (*PUBLIC_ATTRS, "lat", "lon")}
    view = {
        "building_id": b["id"] if b else rec["building_id"],
        "provenance": (rec or {}).get("provenance"),
        "updated": (rec or {}).get("updated"),
        "released": released,
        "attrs": attrs,
        "coverage": {"sessions": sessions, "contributors": contributors, "floors": floors,
                     "status": status, "sessions_needed": s_need or None,
                     "contributors_needed": c_need or None,
                     "k_threshold": {"contributors": cfg.k_contributors, "sessions": cfg.k_sessions}},
        "recompute_pending": bool(stale),
    }
    if released:
        for k in RELEASED_FIELDS:
            view[k] = rec.get(k)
    return view


def summary_properties(view: dict) -> dict:
    """Flat properties for map styling (GeoJSON). Released values only when released."""
    a, c = view["attrs"], view["coverage"]
    p = {"id": view["building_id"], "prov": view["provenance"] or "NONE", "status": c["status"],
         "released": view["released"], "sessions": c["sessions"], "contributors": c["contributors"],
         "sessions_needed": c["sessions_needed"], "name": a.get("name"), "address": a.get("address"),
         "storeys": a.get("storeys")}
    if view["released"]:
        s, st, dr = view["score"], view.get("stiffness") or {}, view.get("drift") or {}
        p.update(score=s["value"], score_lo=s["lo"], score_hi=s["hi"], f1=view.get("f1"),
                 f1_lo=view.get("f1_lo"), f1_hi=view.get("f1_hi"), k_ratio=st.get("k_ratio"),
                 k_flag=bool(st.get("flag")), drift_pct=dr.get("pct_per_year"),
                 drift_alert=bool(dr.get("alert")), class_map=view.get("class_map"))
    return {k: v for k, v in p.items() if v is not None}


def public_card(view: dict, cfg: Config) -> dict:
    """Resident card: coverage, what is still needed, and the score band only when released."""
    c = view["coverage"]
    card = {
        "building_id": view["building_id"], "provenance": view["provenance"],
        "name": view["attrs"].get("name"), "address": view["attrs"].get("address"),
        "status": c["status"], "sessions": c["sessions"], "contributors": c["contributors"],
        "sessions_needed": c["sessions_needed"], "contributors_needed": c["contributors_needed"],
        "score_band": None,
        "caveat": CAVEAT,
        "inspection_route": {
            "text": ("If you are concerned about this building, ask the owner or manager whether a "
                     "seismic evaluation exists, and contact your local building department or a "
                     "licensed structural engineer for an inspection."),
            "url": cfg.inspection_url},
    }
    if c["status"] == "no_data":
        card["message"] = (f"No measurements yet. {cfg.k_contributors} different people and "
                           f"{cfg.k_sessions} sessions are needed before a result is published.")
    elif c["status"] == "needs_data":
        card["message"] = (f"Measurements are being collected. About {c['sessions_needed']} more "
                           "sessions are needed before a result is published.")
    if view["released"]:
        s = view["score"]
        card["score_band"] = {"value": s["value"], "lo": s["lo"], "hi": s["hi"],
                              "interval": "5-95%", "scale": "0-100, 100 = least vulnerable",
                              "provenance": view["provenance"]}
    return card


# ----------------------------------------------------------------------------------------------
# contributor badges (referral loop)

BADGE_TIERS = [(0, "none"), (1, "first_reading"), (5, "regular"), (15, "anchor"), (40, "cornerstone")]


def badges(pseudonym: str, rows: list[dict], cfg: Config) -> dict:
    """Pure function of the building's stored session rows (ordered by t_start, session_id).

    A session counts 2 points if, when it was recorded, the building was still below the
    K-threshold (an under-covered building), otherwise 1 point.
    """
    rows = sorted(rows, key=lambda r: (r["t_start"], r["session_id"]))
    seen_c: set[str] = set()
    n_before = 0
    own = early = points = 0
    for r in rows:
        under = n_before < cfg.k_sessions or len(seen_c) < cfg.k_contributors
        if r["contributor"] == pseudonym:
            own += 1
            early += under
            points += 2 if under else 1
        n_before += 1
        seen_c.add(r["contributor"])
    tier = "none"
    nxt = None
    for i, (lim, name) in enumerate(BADGE_TIERS):
        if points >= lim:
            tier = name
            nxt = BADGE_TIERS[i + 1] if i + 1 < len(BADGE_TIERS) else None
    cov = live_cov(rows)
    s_need, c_need = _needed(cov["sessions"], cov["contributors"], cfg)
    return {"pseudonym": pseudonym, "sessions": own, "under_covered_sessions": early,
            "points": points, "tier": tier,
            "next_tier": None if nxt is None else {"name": nxt[1], "points_needed": nxt[0] - points},
            "pioneer": early > 0,
            "building": {"sessions": cov["sessions"], "contributors": cov["contributors"],
                         "sessions_needed": s_need or None, "contributors_needed": c_need or None},
            "invite_hint": (None if c_need == 0 else
                            f"This building needs {c_need} more contributor(s). Invite a neighbour.")}
