"""API: upload idempotency, location refusal, K-threshold gating on every read endpoint, portfolio
matching by each method, exports, badges, static export."""
from __future__ import annotations

import csv
import gzip
import io
import json
import uuid

import numpy as np
import pytest
from datetime import date
from fastapi.testclient import TestClient

from quakescore.service import codec, export_static, fixtures, load_results
from quakescore.service.app import create_app
from quakescore.service.config import Config
from quakescore.service.store import Store
from tests.test_service_codec import make_features

KEY = {"X-API-Key": "test-key"}
MODAL_KEYS = ("modes", "f1", "f1_lo", "f1_hi", "zeta1", "class_probs", "class_map", "stiffness",
              "score", "damage", "drift", "spectrum")


def square(lon, lat, d=0.0003):
    return {"type": "Polygon", "coordinates": [[[lon, lat], [lon + d, lat], [lon + d, lat + d],
                                                [lon, lat + d], [lon, lat]]]}


# Building A: released. B: record says scored but only 2 contributors (below K). C: record status
# needs_data with parameters present (batch output must still be gated). D: no record at all.
BUILDINGS = {
    "osm:way/100": (-122.4000, 37.7900, "100 Market Street", "Alpha Tower"),
    "osm:way/200": (-122.3990, 37.7900, "200 Market Street", None),
    "osm:way/300": (-122.3980, 37.7900, "300 Mission St", None),
    "osm:way/400": (-122.3970, 37.7900, None, None),
    "osm:way/500": (-122.3960, 37.7900, "500 Howard Street", None),
    "osm:way/501": (-122.3950, 37.7900, "500 Howard Street", None),   # duplicate address
}


def full_record(bid, sessions, contributors, status="scored"):
    lon, lat, addr, name = BUILDINGS[bid]
    rng = np.random.default_rng(int(bid.split("/")[1]))
    props = {"id": bid, "storeys": 8, "height_m": 30.0, "year": 1965, "material": None, "use": None,
             "name": name, "address": addr}
    r = fixtures.make_record(props, lat, lon, rng, date(2026, 11, 1))
    while r["score"] is None:                     # make_record may draw a no_data building
        r = fixtures.make_record(props, lat, lon, rng, date(2026, 11, 1))
    r["coverage"].update(sessions=sessions, contributors=contributors, floors=3, status=status,
                         sessions_needed=None)
    return r


@pytest.fixture()
def world(tmp_path):
    cfg = Config(db_path=str(tmp_path / "t.sqlite"), blob_dir=None, k_contributors=3, k_sessions=5,
                 api_keys=("test-key",), cors_origins=("*",), inspection_url="https://example.org/inspect",
                 max_upload_bytes=2 * 1024 * 1024)
    st = Store(cfg.db_path)
    for bid, (lon, lat, addr, name) in BUILDINGS.items():
        st.upsert_building(bid, square(lon, lat), {"storeys": 8, "name": name, "address": addr})
    rep = load_results.load(st, [full_record("osm:way/100", 12, 4),
                                 full_record("osm:way/200", 9, 2),
                                 full_record("osm:way/300", 6, 3, status="needs_data")])
    assert rep["rejected"] == 0
    client = TestClient(create_app(st, cfg))
    return client, st, cfg


def upload(client, sf, gz=True, extra=None):
    p = codec.encode(sf)
    if extra:
        p.update(extra)
    body = json.dumps(p).encode()
    headers = {"Content-Type": "application/json"}
    if gz:
        body = gzip.compress(body)
        headers["Content-Encoding"] = "gzip"
    return client.post("/v1/sessions", content=body, headers=headers)


def no_modal(obj):
    assert not any(k in obj and obj[k] is not None for k in MODAL_KEYS), obj


# ---------------------------------------------------------------- upload

def test_upload_and_idempotency(world):
    client, st, _ = world
    sf = make_features(building_id="osm:way/400")
    r = upload(client, sf)
    assert r.status_code == 201 and r.json()["status"] == "stored"
    r2 = upload(client, sf)
    assert r2.status_code == 200 and r2.json()["status"] == "duplicate"
    r3 = upload(client, sf, gz=False)
    assert r3.status_code == 200 and r3.json()["status"] == "duplicate"
    assert st.count_sessions() == 1
    # stored features decode back to the same arrays
    back = codec.decode(st.session_payload(sf.session_id))
    assert (back.bands["M"].csd == sf.bands["M"].csd.astype("complex64")).all()
    row = st.db.execute("SELECT * FROM sessions").fetchone()
    assert len(row["received"]) == 10                     # date only
    assert not any(codec.looks_like_location(k) for k in json.loads(row["metadata"]))
    assert not any(codec.looks_like_location(k) or k in ("host", "client", "user_agent")
                   for k in row.keys())


def test_upload_location_refused(world):
    client, st, _ = world
    for f in ("lat", "lon", "gps", "location"):
        r = upload(client, make_features(building_id="osm:way/400"), extra={f: 37.79})
        assert r.status_code == 422, r.text
        assert "location" in r.json()["detail"]["error"]
    assert st.count_sessions() == 0


def test_upload_bad_inputs(world):
    client, _, _ = world
    assert client.post("/v1/sessions", content=b"\x1f\x8bnotgzip").status_code == 400
    assert client.post("/v1/sessions", content=b"{not json").status_code == 400
    assert client.post("/v1/sessions", content=b'{"schema": NaN}').status_code == 400
    r = upload(client, make_features(building_id="osm:way/999999"))
    assert r.status_code == 422 and r.json()["detail"]["field"] == "building_id"


def test_uploads_raise_coverage_but_do_not_release(world):
    client, _, _ = world
    for i in range(6):
        sf = make_features(building_id="osm:way/400", contributor=f"{i:016x}")
        assert upload(client, sf).status_code == 201
    v = client.get("/v1/buildings/osm:way/400", headers=KEY).json()
    assert v["coverage"]["sessions"] == 6 and v["coverage"]["contributors"] == 6
    assert v["coverage"]["status"] == "needs_data"        # no batch record yet -> nothing released
    assert v["released"] is False
    no_modal(v)


# ---------------------------------------------------------------- K-threshold on every read path

def test_gate_building_detail(world):
    client, _, _ = world
    a = client.get("/v1/buildings/osm:way/100", headers=KEY).json()
    assert a["released"] and a["provenance"] == "FIXTURE"
    assert {"value", "lo", "hi"} <= set(a["score"]) and a["score"]["lo"] <= a["score"]["value"] <= a["score"]["hi"]
    assert a["f1_lo"] <= a["f1"] <= a["f1_hi"]
    for bid in ("osm:way/200", "osm:way/300", "osm:way/400"):
        v = client.get(f"/v1/buildings/{bid}", headers=KEY).json()
        assert v["released"] is False
        no_modal(v)
    assert client.get("/v1/buildings/osm:way/200", headers=KEY).json()["coverage"]["status"] == "needs_data"
    assert client.get("/v1/buildings/osm:way/400", headers=KEY).json()["coverage"]["status"] == "no_data"
    assert client.get("/v1/buildings/osm:way/200", headers=KEY).json()["coverage"]["contributors_needed"] == 1


def test_k_threshold_configurable(world, tmp_path):
    _, st, cfg = world
    lax = Config(**{**cfg.__dict__, "k_contributors": 2})
    c2 = TestClient(create_app(st, lax))
    assert c2.get("/v1/buildings/osm:way/200", headers=KEY).json()["released"] is True
    strict = Config(**{**cfg.__dict__, "k_sessions": 50})
    c3 = TestClient(create_app(st, strict))
    assert c3.get("/v1/buildings/osm:way/100", headers=KEY).json()["released"] is False


def test_gate_listing_coverage_public_exports(world):
    client, _, _ = world
    fc = client.get("/v1/buildings", headers=KEY).json()
    props = {f["properties"]["id"]: f["properties"] for f in fc["features"]}
    assert "score" in props["osm:way/100"] and "score_lo" in props["osm:way/100"]
    for bid in ("osm:way/200", "osm:way/300", "osm:way/400"):
        assert not ({"score", "score_lo", "f1", "k_ratio", "drift_pct", "class_map"} & set(props[bid]))
    # score filters only return released buildings
    s = props["osm:way/100"]["score"]
    ids = [f["id"] for f in client.get(f"/v1/buildings?min_score=0&max_score=100", headers=KEY).json()["features"]]
    assert ids == ["osm:way/100"]
    assert client.get(f"/v1/buildings?min_score={s + 0.1}", headers=KEY).json()["features"] == []
    st_ids = [f["id"] for f in client.get("/v1/buildings?status=needs_data", headers=KEY).json()["features"]]
    assert set(st_ids) == {"osm:way/200", "osm:way/300"}
    bb = client.get("/v1/buildings?bbox=-122.4001,37.7899,-122.3995,37.7905", headers=KEY).json()
    assert [f["id"] for f in bb["features"]] == ["osm:way/100"]
    assert client.get("/v1/buildings?bbox=1,2,3", headers=KEY).status_code == 422

    cov = client.get("/v1/coverage").json()
    for f in cov["features"]:
        assert set(f["properties"]) <= {"id", "status", "sessions", "contributors", "floors",
                                        "sessions_needed", "contributors_needed", "provenance"}
    assert cov["meta"]["counts"] == {"scored": 1, "needs_data": 2, "no_data": 3}

    for bid in ("osm:way/200", "osm:way/300", "osm:way/400"):
        card = client.get(f"/v1/buildings/{bid}/public").json()
        assert card["score_band"] is None and "not a structural engineering assessment" in card["caveat"]
        assert card["inspection_route"]["url"] == "https://example.org/inspect"
        no_modal(card)
    card = client.get("/v1/buildings/osm:way/100/public").json()
    assert card["score_band"]["lo"] <= card["score_band"]["value"] <= card["score_band"]["hi"]
    assert card["score_band"]["provenance"] == "FIXTURE"
    assert client.get("/v1/buildings/osm:way/400/public").json()["sessions_needed"] == 5

    rows = list(csv.DictReader(io.StringIO(client.get("/v1/export.csv", headers=KEY).text)))
    assert [r["building_id"] for r in rows] == ["osm:way/100"]
    assert rows[0]["score_lo"] and rows[0]["score_hi"] and rows[0]["provenance"] == "FIXTURE"
    gj = client.get("/v1/export.geojson", headers=KEY).json()
    assert [f["id"] for f in gj["features"]] == ["osm:way/100"]
    assert gj["features"][0]["properties"]["score_lo"] is not None


def test_buyer_endpoints_need_key(world):
    client, _, _ = world
    for path in ("/v1/buildings", "/v1/buildings/osm:way/100", "/v1/export.csv", "/v1/export.geojson"):
        assert client.get(path).status_code == 401
        assert client.get(path, headers={"X-API-Key": "wrong"}).status_code == 401
    assert client.post("/v1/portfolio", content=b"building_id\nosm:way/100\n").status_code == 401
    # public endpoints work without a key
    assert client.get("/v1/coverage").status_code == 200
    assert client.get("/v1/buildings/osm:way/100/public").status_code == 200
    assert client.get("/v1/meta").status_code == 200


def test_score_without_band_never_released(world):
    client, st, _ = world
    r = full_record("osm:way/400", 20, 6)
    r["score"] = {"value": 50.0}
    with pytest.raises(Exception):
        load_results.validate_record(r)
    st.put_result(r)                              # even if written directly, the gate refuses it
    v = client.get("/v1/buildings/osm:way/400", headers=KEY).json()
    assert v["released"] is False
    no_modal(v)


def test_footprints_endpoint(world):
    client, st, _ = world
    far = square(-122.3800, 37.7900)                # ~1.8 km east: outside +-0.01 deg
    edge = square(-122.4099, 37.7999, d=0.0005)     # straddles the box corner
    st.upsert_building("osm:way/700", far, {})
    st.upsert_building("osm:way/701", edge, {})
    r = client.get("/v1/footprints?lat=37.79&lon=-122.40").json()
    ids = {f["id"] for f in r["features"]}
    assert set(BUILDINGS) | {"osm:way/701"} == ids          # every footprint within +-0.01 deg
    assert r["box_deg"] == 0.01 and "lat" not in r and "lon" not in r
    assert set(r["features"][0]["properties"]) == {"id", "name", "address", "storeys"}
    from quakescore.service import cells
    c = cells.latlng_to_cell(37.7901, -122.3999)
    r2 = client.get(f"/v1/footprints?cell={c}&ring=1").json()
    assert "osm:way/100" in {f["id"] for f in r2["features"]}
    assert client.get("/v1/footprints").status_code == 422
    assert client.get("/v1/footprints?cell=bogus").status_code == 422
    assert client.get("/v1/footprints?lat=91&lon=0").status_code == 422


def test_privacy_scrub_middleware():
    import asyncio
    from quakescore.service.app import PrivacyScrubMiddleware
    seen = {}

    async def inner(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    async def send(msg):
        if msg["type"] == "http.response.start":     # what an access logger would read now
            seen["qs"], seen["client"] = scope["query_string"], scope["client"]

    scope = {"type": "http", "path": "/v1/footprints", "query_string": b"lat=37.79&lon=-122.40",
             "client": ("203.0.113.9", 5555)}
    asyncio.run(PrivacyScrubMiddleware(inner)(scope, None, send))
    assert seen == {"qs": b"", "client": None}
    scope = {"type": "http", "path": "/v1/sessions/6736a91a-62cc-4625-979d-ce9bce1dd4f2",
             "raw_path": b"/v1/sessions/6736a91a-62cc-4625-979d-ce9bce1dd4f2", "query_string": b"",
             "client": ("203.0.113.9", 5555)}
    asyncio.run(PrivacyScrubMiddleware(inner)(scope, None, send))
    assert "6736a91a" not in scope["path"] and b"6736a91a" not in scope["raw_path"]


def test_delete_session(world):
    client, st, cfg = world
    sids = []
    for i in range(5):
        sf = make_features(building_id="osm:way/400", contributor=f"{i + 1:016x}")
        assert upload(client, sf).status_code == 201
        sids.append(sf.session_id)
    # a batch record computed from those 5 sessions / 5 contributors -> released
    rec = full_record("osm:way/100", 5, 5)
    rec["building_id"] = "osm:way/400"
    load_results.load(st, [rec])
    assert client.get("/v1/buildings/osm:way/400", headers=KEY).json()["released"] is True
    r = client.delete(f"/v1/sessions/{sids[0]}")
    assert r.status_code == 204 and r.content == b""
    assert st.count_sessions() == 4 and not st.has_session(sids[0])
    assert st.needs_recompute("osm:way/400")
    # idempotent and not probeable: same answer for a repeat and for an id that never existed
    assert client.delete(f"/v1/sessions/{sids[0]}").status_code == 204
    assert client.delete(f"/v1/sessions/{uuid.uuid4()}").status_code == 204
    assert client.delete("/v1/sessions/not-a-uuid").status_code == 422
    # stale record: live counts (4 sessions) are below K -> withheld everywhere
    v = client.get("/v1/buildings/osm:way/400", headers=KEY).json()
    assert v["released"] is False and v["recompute_pending"] is True
    assert v["coverage"]["sessions"] == 4
    no_modal(v)
    assert client.get("/v1/buildings/osm:way/400/public").json()["score_band"] is None
    assert "osm:way/400" not in [r["building_id"] for r in
                                 csv.DictReader(io.StringIO(client.get("/v1/export.csv", headers=KEY).text))]
    # a fresh batch record clears the recompute mark
    load_results.load(st, [rec])
    assert not st.needs_recompute("osm:way/400")


# ---------------------------------------------------------------- portfolio

def test_portfolio_each_method(world):
    client, _, _ = world
    csv_text = "\n".join([
        "ref,building_id,lat,lon,address",
        "a,osm:way/100,,,",                                   # building_id
        "b,,37.79015,-122.39985,",                            # inside osm:way/100
        f"c,,{37.7900 - 15 / 111320:.7f},-122.39985,",        # 15 m south of osm:way/100
        f"d,,{37.7900 - 60 / 111320:.7f},-122.39985,",        # 60 m away: unmatched
        "e,,,,\"300 Mission Street, San Francisco, CA\"",     # address (St -> Street)
        "f,,,,500 Howard St",                                 # ambiguous
        "g,osm:way/999,37.79015,-122.39885,",                 # bad id, falls back to lat/lon
        "h,,,,",                                              # invalid
    ])
    r = client.post("/v1/portfolio", headers=KEY, files={"file": ("p.csv", csv_text, "text/csv")})
    assert r.status_code == 200, r.text
    res = r.json()
    rows = {x["ref"]: x for x in res["rows"]}
    assert rows["a"]["match_method"] == "building_id" and rows["a"]["building_id"] == "osm:way/100"
    assert rows["b"]["match_method"] == "point_in_polygon" and rows["b"]["distance_m"] == 0
    assert rows["c"]["match_method"] == "nearest_footprint" and 14 <= rows["c"]["distance_m"] <= 16
    assert rows["c"]["building_id"] == "osm:way/100"
    assert rows["d"]["match_status"] == "unmatched"
    assert rows["e"]["match_method"] == "address" and rows["e"]["building_id"] == "osm:way/300"
    assert rows["f"]["match_status"] == "ambiguous" and set(rows["f"]["candidates"]) == {"osm:way/500", "osm:way/501"}
    assert rows["g"]["building_id"] == "osm:way/200" and "not found" in rows["g"]["note"]
    assert rows["h"]["match_status"] == "invalid"
    # scores only for released buildings, always with band
    assert rows["a"]["score"]["lo"] <= rows["a"]["score"]["value"] <= rows["a"]["score"]["hi"]
    assert rows["a"]["f1"]["lo"] <= rows["a"]["f1"]["value"] <= rows["a"]["f1"]["hi"]
    assert rows["e"]["score"] is None and rows["e"]["f1"] is None and rows["e"]["coverage_status"] == "needs_data"
    assert rows["g"]["score"] is None
    s = res["summary"]
    assert s["rows"] == 8 and s["matched"] == 5 and s["scored"] == 3 and s["ambiguous"] == 1
    assert s["coverage_pct"] == 60.0
    assert sum(b["count"] for b in s["score_distribution"]["bins"]) == 3
    job = client.get(f"/v1/portfolio/{res['job_id']}", headers=KEY).json()
    assert job["summary"] == s
    # raw text/csv body also accepted
    r2 = client.post("/v1/portfolio", headers={**KEY, "Content-Type": "text/csv"},
                     content="latitude,longitude\n37.79015,-122.39985\n")
    assert r2.json()["rows"][0]["building_id"] == "osm:way/100"
    assert client.post("/v1/portfolio", headers=KEY, content="foo,bar\n1,2\n").status_code == 422


# ---------------------------------------------------------------- badges

def test_badges(world):
    client, _, _ = world
    me = "aaaaaaaaaaaaaaaa"
    t0 = 1_790_000_040.0
    for i in range(3):
        upload(client, make_features(building_id="osm:way/400", contributor=me, t_start=t0 + 60 * i))
    for i in range(4):
        upload(client, make_features(building_id="osm:way/400", contributor=f"{i + 1:016x}",
                                     t_start=t0 + 600 + 60 * i))
    upload(client, make_features(building_id="osm:way/400", contributor=me, t_start=t0 + 3600))
    b = client.get(f"/v1/contributors/{me}/badges?building_id=osm:way/400").json()
    assert b["sessions"] == 4 and b["under_covered_sessions"] == 3 and b["points"] == 7
    assert b["tier"] == "regular" and b["pioneer"] is True
    other = client.get("/v1/contributors/ffffffffffffffff/badges?building_id=osm:way/400").json()
    assert other["tier"] == "none" and other["points"] == 0
    assert client.get("/v1/contributors/XYZ/badges?building_id=osm:way/400").status_code == 422
    assert client.get(f"/v1/contributors/{me}/badges?building_id=osm:way/9").status_code == 404


# ---------------------------------------------------------------- static export

def test_static_export_is_gated(world, tmp_path):
    _, st, cfg = world
    out = tmp_path / "static"
    meta = export_static.export(st, cfg, out)
    assert meta["buildings"] == 6
    fc = json.loads((out / "buildings.geojson").read_text())
    for f in fc["features"]:
        p = f["properties"]
        d = json.loads((out / "b" / p["file"]).read_text())
        if p["id"] == "osm:way/100":
            assert d["released"] and d["score"]["lo"] <= d["score"]["value"]
        else:
            assert not d["released"] and "score" not in p
            no_modal(d)
