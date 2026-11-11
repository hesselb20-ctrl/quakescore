"""Upload codec: round trip and strict validation."""
from __future__ import annotations

import base64
import copy
import uuid

import numpy as np
import pytest

from quakescore.features import NBINS, BandFeatures, SessionFeatures
from quakescore.service import cells, codec, geo


def make_features(rng=None, building_id="osm:way/1", contributor="0123456789abcdef",
                  provenance="REAL", t_start=1_790_000_040.0) -> SessionFeatures:
    rng = rng or np.random.default_rng(0)
    bands = {}
    for name in ("L", "M", "H"):
        X = (rng.normal(size=(8, NBINS, 3)) + 1j * rng.normal(size=(8, NBINS, 3))) * 1e-4
        csd = np.einsum("wfi,wfj->fij", X, X.conj()) / 8
        p4 = (np.abs(X) ** 4).mean(0)
        bands[name] = BandFeatures(k=8, csd=csd.astype(np.complex64), p4=p4.astype(np.float32))
    return SessionFeatures(
        session_id=str(uuid.uuid4()), building_id=building_id, contributor=contributor,
        phone_model="Pixel 8", floor=4, floor_method="baro_entry", t_start=t_start,
        duration=3600.0, fs_raw=203.7, lsb=0.0012, sync_source="ntp", sync_sigma_ms=12.0,
        accept_fraction=0.81, bands=bands, temp_c=27.5, provenance=provenance)


def test_round_trip_exact_float32():
    sf = make_features()
    p = codec.encode(sf, {"sensor_name": "LSM6DSO", "platform": "android", "app_version": "0.3.1"})
    assert "provenance" not in p                      # real uploads carry no provenance field
    back = codec.decode(p)
    assert back.provenance == "REAL"
    assert back.session_id == sf.session_id and back.building_id == sf.building_id
    assert back.t_start == sf.t_start and back.floor == 4 and back.temp_c == 27.5
    for name, b in sf.bands.items():
        bb = back.bands[name]
        assert bb.k == b.k
        assert bb.csd.shape == (NBINS, 3, 3) and bb.p4.shape == (NBINS, 3)
        np.testing.assert_array_equal(bb.csd, b.csd.astype(np.complex64))
        np.testing.assert_array_equal(bb.p4, b.p4)
        # Hermitian rebuilt
        np.testing.assert_array_equal(bb.csd, np.conj(np.transpose(bb.csd, (0, 2, 1))))
    # derived quantities identical
    np.testing.assert_array_equal(back.trace("M"), sf.trace("M").astype(back.trace("M").dtype))


def test_packing_order():
    sf = make_features()
    v = codec.pack_csd(sf.bands["L"].csd)
    c = sf.bands["L"].csd
    np.testing.assert_array_equal(v[:, 3], c[:, 0, 1].real.astype(np.float32))
    np.testing.assert_array_equal(v[:, 6], c[:, 0, 2].imag.astype(np.float32))
    np.testing.assert_array_equal(v[:, 8], c[:, 1, 2].imag.astype(np.float32))
    raw = base64.b64decode(codec.encode(sf)["bands"]["L"]["csd"])
    assert len(raw) == NBINS * 9 * 4
    assert np.frombuffer(raw, "<f4")[9] == np.float32(c[1, 0, 0].real)   # bin 1, Gxx


def test_sim_provenance_round_trip_and_sim_floor_method():
    sf = make_features(provenance="SIM")
    sf.floor_method = "sim"
    p = codec.encode(sf)
    assert p["provenance"] == "SIM"
    assert codec.decode(p).provenance == "SIM"
    p2 = dict(p)
    p2.pop("provenance")
    with pytest.raises(codec.CodecError) as e:      # "sim" floor method only on SIM payloads
        codec.decode(p2)
    assert e.value.field == "floor_method"


@pytest.mark.parametrize("field", ["lat", "lon", "latitude", "lng", "gps", "location", "geo",
                                   "coords", "gpsFix", "altitude", "wifi_bssid", "ip", "address",
                                   "loc_accuracy", "cell_id", "h3"])
def test_location_fields_rejected(field):
    p = codec.encode(make_features())
    p[field] = 37.79
    with pytest.raises(codec.CodecError) as e:
        codec.decode(p)
    assert "location" in e.value.msg


def test_location_inside_band_rejected():
    p = codec.encode(make_features())
    p["bands"]["L"]["lat"] = 1.0
    with pytest.raises(codec.CodecError):
        codec.decode(p)


def test_unknown_field_rejected():
    p = codec.encode(make_features())
    p["extra"] = 1
    with pytest.raises(codec.CodecError) as e:
        codec.decode(p)
    assert "unknown" in e.value.msg


def _bad(mut):
    p = codec.encode(make_features())
    mut(p)
    with pytest.raises(codec.CodecError):
        codec.decode(p)


def test_strict_validation():
    _bad(lambda p: p.update(schema=2))
    _bad(lambda p: p.update(session_id="not-a-uuid"))
    _bad(lambda p: p.update(session_id=str(uuid.uuid1())))
    _bad(lambda p: p.update(contributor="XYZ"))
    _bad(lambda p: p.update(building_id="no spaces allowed"))
    _bad(lambda p: p.update(floor=2.5))
    _bad(lambda p: p.update(floor_method="guess"))
    _bad(lambda p: p.update(t_start=p["t_start"] + 7))           # not rounded to the minute
    _bad(lambda p: p.update(t_start=1e12))                       # in the future
    _bad(lambda p: p.update(fs_raw=float("nan")))
    _bad(lambda p: p.update(accept_fraction=1.5))
    _bad(lambda p: p.update(charging=1))
    _bad(lambda p: p.update(battery_start=101))
    _bad(lambda p: p.update(platform="windows"))
    _bad(lambda p: p.pop("temp_c"))
    _bad(lambda p: p.update(provenance="FIXTURE"))
    _bad(lambda p: p.update(bands={}))
    _bad(lambda p: p["bands"].update(X=p["bands"]["L"]))
    _bad(lambda p: p["bands"]["L"].update(k=-1))
    _bad(lambda p: p["bands"]["L"].update(k=True))
    _bad(lambda p: p["bands"]["L"].update(csd=p["bands"]["L"]["csd"][:-8]))   # wrong size
    _bad(lambda p: p["bands"]["L"].update(csd="!!!notbase64"))

    def nan_csd(p):
        a = np.frombuffer(base64.b64decode(p["bands"]["M"]["csd"]), "<f4").copy()
        a[100] = np.nan
        p["bands"]["M"]["csd"] = base64.b64encode(a.tobytes()).decode()
    _bad(nan_csd)

    def neg_auto(p):
        a = np.frombuffer(base64.b64decode(p["bands"]["M"]["csd"]), "<f4").copy()
        a[9 * 10 + 1] = -1.0          # Gyy at bin 10
        p["bands"]["M"]["csd"] = base64.b64encode(a.tobytes()).decode()
    _bad(neg_auto)


def test_partial_bands_ok():
    p = codec.encode(make_features())
    p["bands"] = {"M": p["bands"]["M"]}
    sf = codec.decode(p)
    assert list(sf.bands) == ["M"]


def test_cells_and_geo():
    c = cells.latlng_to_cell(37.7915, -122.3985)
    assert cells.is_valid_cell(c)
    assert 0.5 < cells.cell_area_km2(c) < 1.0
    disk = cells.grid_disk(c, 1)
    assert c in disk and 7 <= len(disk) <= 12
    w, s, e, n = cells.cell_bbox(c)
    assert w <= -122.3985 <= e and s <= 37.7915 <= n
    sq = {"type": "Polygon", "coordinates": [[[-122.4, 37.79], [-122.3995, 37.79], [-122.3995, 37.7904],
                                              [-122.4, 37.7904], [-122.4, 37.79]]]}
    lat, lon = geo.centroid(sq)
    assert abs(lat - 37.7902) < 1e-9 and abs(lon + 122.39975) < 1e-9
    assert geo.contains(sq, 37.7902, -122.3997)
    assert not geo.contains(sq, 37.7910, -122.3997)
    d = geo.distance_m(sq, 37.7904 + 20 / 111320, -122.3997)
    assert abs(d - 20) < 0.5
