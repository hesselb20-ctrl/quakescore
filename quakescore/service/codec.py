"""Upload codec: the JSON message a phone POSTs to /v1/sessions (gzip-compressed), schema 1.

    encode(SessionFeatures, meta=None) -> dict      (simulator, tests, test vectors)
    decode(dict) -> SessionFeatures                 (server)
    validate(dict) -> Upload(features, meta)        (server; decode plus the extra metadata)

Validation is strict. Any field that is not part of schema 1 is refused, and a field whose name looks
like location (lat, lon, gps, location, ...) is refused with an explicit message, so that a location
can never be stored by accident. Tier-B sync frames are not part of schema 1 and are not encoded.

csd packing per bin (float32 little endian, 9 values):
    Gxx, Gyy, Gzz, Re Gxy, Im Gxy, Re Gxz, Im Gxz, Re Gyz, Im Gyz
p4 packing per bin (float32 little endian, 3 values): mean |X_x|^4, |X_y|^4, |X_z|^4
"""
from __future__ import annotations

import base64
import binascii
import math
import re
import time
import uuid
from dataclasses import dataclass

import numpy as np

from quakescore.features import BANDS, NBINS, BandFeatures, SessionFeatures

SCHEMA = 1
FLOOR_METHODS = {"baro_entry", "baro_ref", "manual"}
SIM_FLOOR_METHODS = {"sim"}           # accepted only on provenance "SIM" payloads
SYNC_SOURCES = {"gnss", "ntp", "none"}
PLATFORMS = {"android", "ios"}
PROVENANCES = {"REAL", "SIM"}         # "provenance" is only ever set by the simulator

FIELDS = {
    "schema", "session_id", "building_id", "contributor", "phone_model", "sensor_name", "floor",
    "floor_method", "t_start", "duration", "fs_raw", "lsb", "sync_source", "sync_sigma_ms",
    "accept_fraction", "temp_c", "battery_start", "battery_end", "charging", "platform",
    "app_version", "bands", "provenance",
}
BAND_FIELDS = {"k", "csd", "p4"}

LOCATION_RE = re.compile(
    r"(^|_)(lat|lats|latitude|lon|lng|long|longitude|gps|gnss_fix|geo|geohash|location|loc|"
    r"coord|coords|coordinates|position|pos|altitude|alt|address|addr|wifi|ssid|bssid|"
    r"cell_?id|mcc|mnc|ip|ip_?address|place|plus_?code|h3|cell)($|_)")

BUILDING_ID_RE = re.compile(r"^[a-z][a-z0-9_]{0,15}:[A-Za-z0-9_./-]{1,80}$")
CONTRIBUTOR_RE = re.compile(r"^[0-9a-f]{16}$")
SAFE_TEXT_RE = re.compile(r"^[\x20-\x7e]{1,128}$")

T_MIN = 1_577_836_800.0               # 2020-01-01T00:00Z
MAX_SPECTRAL = 1e6                    # (m/s^2)^2/Hz; far above any phone at rest
CSD_BYTES = NBINS * 9 * 4
P4_BYTES = NBINS * 3 * 4


class CodecError(ValueError):
    """Validation failure. `field` names the offending field; HTTP layer maps this to 422."""

    def __init__(self, field: str, msg: str):
        super().__init__(f"{field}: {msg}")
        self.field = field
        self.msg = msg


@dataclass
class Upload:
    features: SessionFeatures
    meta: dict          # every validated scalar field except bands (no location by construction)


def looks_like_location(name: str) -> bool:
    n = re.sub(r"(?<=[a-z])(?=[A-Z])", "_", str(name)).lower().replace("-", "_")
    return bool(LOCATION_RE.search(n))


# ----------------------------------------------------------------------------------------------
# encode

def _b64(a: np.ndarray) -> str:
    return base64.b64encode(np.ascontiguousarray(a, dtype="<f4").tobytes()).decode("ascii")


def pack_csd(csd: np.ndarray) -> np.ndarray:
    c = np.asarray(csd)
    out = np.empty((NBINS, 9), np.float32)
    out[:, 0] = c[:, 0, 0].real
    out[:, 1] = c[:, 1, 1].real
    out[:, 2] = c[:, 2, 2].real
    out[:, 3], out[:, 4] = c[:, 0, 1].real, c[:, 0, 1].imag
    out[:, 5], out[:, 6] = c[:, 0, 2].real, c[:, 0, 2].imag
    out[:, 7], out[:, 8] = c[:, 1, 2].real, c[:, 1, 2].imag
    return out


def unpack_csd(v: np.ndarray) -> np.ndarray:
    c = np.zeros((NBINS, 3, 3), np.complex64)
    c[:, 0, 0] = v[:, 0]
    c[:, 1, 1] = v[:, 1]
    c[:, 2, 2] = v[:, 2]
    c[:, 0, 1] = v[:, 3] + 1j * v[:, 4]
    c[:, 0, 2] = v[:, 5] + 1j * v[:, 6]
    c[:, 1, 2] = v[:, 7] + 1j * v[:, 8]
    c[:, 1, 0] = np.conj(c[:, 0, 1])
    c[:, 2, 0] = np.conj(c[:, 0, 2])
    c[:, 2, 1] = np.conj(c[:, 1, 2])
    return c


META_DEFAULTS = {"sensor_name": "unknown", "battery_start": 100, "battery_end": 100,
                 "charging": True, "platform": "android", "app_version": "0.0.0"}


def encode(sf: SessionFeatures, meta: dict | None = None) -> dict:
    """SessionFeatures -> schema-1 upload dict. `meta` supplies fields SessionFeatures lacks
    (sensor_name, battery_start, battery_end, charging, platform, app_version)."""
    m = dict(META_DEFAULTS)
    m.update(meta or {})
    out = {
        "schema": SCHEMA, "session_id": sf.session_id, "building_id": sf.building_id,
        "contributor": sf.contributor, "phone_model": sf.phone_model,
        "sensor_name": m["sensor_name"], "floor": int(sf.floor), "floor_method": sf.floor_method,
        "t_start": float(60 * round(sf.t_start / 60)), "duration": float(sf.duration),
        "fs_raw": float(sf.fs_raw), "lsb": float(sf.lsb), "sync_source": sf.sync_source,
        "sync_sigma_ms": float(sf.sync_sigma_ms), "accept_fraction": float(sf.accept_fraction),
        "temp_c": None if sf.temp_c is None else float(sf.temp_c),
        "battery_start": int(m["battery_start"]), "battery_end": int(m["battery_end"]),
        "charging": bool(m["charging"]), "platform": m["platform"],
        "app_version": str(m["app_version"]),
        "bands": {name: {"k": int(b.k), "csd": _b64(pack_csd(b.csd)), "p4": _b64(b.p4)}
                  for name, b in sf.bands.items()},
    }
    if sf.provenance == "SIM":
        out["provenance"] = "SIM"
    return out


# ----------------------------------------------------------------------------------------------
# decode / validate

def _num(p: dict, k: str, lo: float, hi: float, *, integer=False, nullable=False):
    if k not in p:
        if nullable:
            return None
        raise CodecError(k, "required")
    v = p[k]
    if v is None:
        if nullable:
            return None
        raise CodecError(k, "must not be null")
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise CodecError(k, "must be a number")
    if integer and not (isinstance(v, int) or float(v).is_integer()):
        raise CodecError(k, "must be an integer")
    if not math.isfinite(float(v)):
        raise CodecError(k, "must be finite")
    if not lo <= v <= hi:
        raise CodecError(k, f"out of range [{lo}, {hi}]")
    return int(v) if integer else float(v)


def _enum(p: dict, k: str, allowed: set[str]) -> str:
    v = p.get(k)
    if not isinstance(v, str) or v not in allowed:
        raise CodecError(k, f"must be one of {sorted(allowed)}")
    return v


def _text(p: dict, k: str) -> str:
    v = p.get(k)
    if not isinstance(v, str) or not SAFE_TEXT_RE.match(v):
        raise CodecError(k, "must be 1-128 printable ASCII characters")
    return v


def _array(s, field: str, nbytes: int, ncols: int) -> np.ndarray:
    if not isinstance(s, str):
        raise CodecError(field, "must be a base64 string")
    try:
        raw = base64.b64decode(s, validate=True)
    except (binascii.Error, ValueError):
        raise CodecError(field, "invalid base64") from None
    if len(raw) != nbytes:
        raise CodecError(field, f"expected {nbytes} bytes, got {len(raw)}")
    a = np.frombuffer(raw, dtype="<f4").reshape(NBINS, ncols)
    if not np.all(np.isfinite(a)):
        raise CodecError(field, "contains non-finite values")
    if np.max(np.abs(a)) > MAX_SPECTRAL ** (2 if ncols == 3 else 1):
        raise CodecError(field, "implausibly large values")
    return a.astype(np.float32)


def _check_fields(p: dict, allowed: set[str], where: str):
    for k in p:
        if k in allowed:
            continue
        if looks_like_location(k):
            raise CodecError(f"{where}{k}", "location fields are never accepted; only the "
                             "building id may identify where a session was recorded")
        raise CodecError(f"{where}{k}", "unknown field (schema 1)")


def validate(p: dict, *, now: float | None = None) -> Upload:
    if not isinstance(p, dict):
        raise CodecError("$", "payload must be a JSON object")
    _check_fields(p, FIELDS, "")
    if p.get("schema") != SCHEMA or isinstance(p.get("schema"), bool):
        raise CodecError("schema", f"must be {SCHEMA}")
    now = time.time() if now is None else now

    sid = p.get("session_id")
    try:
        u = uuid.UUID(str(sid))
        if u.version != 4 or str(u) != str(sid).lower():
            raise ValueError
    except (ValueError, AttributeError, TypeError):
        raise CodecError("session_id", "must be a canonical uuid4 string") from None
    bid = p.get("building_id")
    if not isinstance(bid, str) or not BUILDING_ID_RE.match(bid):
        raise CodecError("building_id", "must look like 'osm:way/123'")
    con = p.get("contributor")
    if not isinstance(con, str) or not CONTRIBUTOR_RE.match(con):
        raise CodecError("contributor", "must be 16 lowercase hex characters")

    prov = p.get("provenance", "REAL")
    if prov not in PROVENANCES:
        raise CodecError("provenance", f"must be one of {sorted(PROVENANCES)}")
    floor_methods = FLOOR_METHODS | (SIM_FLOOR_METHODS if prov == "SIM" else set())

    t_start = _num(p, "t_start", T_MIN, now + 2 * 86400)
    if t_start % 60 != 0:
        raise CodecError("t_start", "must be rounded to the minute")
    if "temp_c" not in p:
        raise CodecError("temp_c", "required (may be null)")
    charging = p.get("charging")
    if not isinstance(charging, bool):
        raise CodecError("charging", "must be true or false")

    meta = {
        "schema": SCHEMA,
        "phone_model": _text(p, "phone_model"),
        "sensor_name": _text(p, "sensor_name"),
        "floor": _num(p, "floor", -10, 200, integer=True),
        "floor_method": _enum(p, "floor_method", floor_methods),
        "t_start": t_start,
        "duration": _num(p, "duration", 60, 7 * 86400),
        "fs_raw": _num(p, "fs_raw", 20, 2000),
        "lsb": _num(p, "lsb", 0, 1),
        "sync_source": _enum(p, "sync_source", SYNC_SOURCES),
        "sync_sigma_ms": _num(p, "sync_sigma_ms", -1, 1e7),
        "accept_fraction": _num(p, "accept_fraction", 0, 1),
        "temp_c": _num(p, "temp_c", -40, 90, nullable=True),
        # null when the platform exposes no battery level (browsers on iOS)
        "battery_start": _num(p, "battery_start", 0, 100, integer=True, nullable=True),
        "battery_end": _num(p, "battery_end", 0, 100, integer=True, nullable=True),
        "charging": charging,
        "platform": _enum(p, "platform", PLATFORMS),
        "app_version": _text(p, "app_version"),
        "provenance": prov,
    }
    if meta["lsb"] <= 0:
        raise CodecError("lsb", "must be positive")
    # -1 is the agreed value for "uncertainty unknown" and is only valid without a sync source
    if meta["sync_sigma_ms"] < 0 and not (meta["sync_sigma_ms"] == -1 and meta["sync_source"] == "none"):
        raise CodecError("sync_sigma_ms", "must be >= 0, or exactly -1 with sync_source 'none'")

    bands_in = p.get("bands")
    if not isinstance(bands_in, dict) or not bands_in:
        raise CodecError("bands", "must be a non-empty object")
    bands = {}
    for name, b in bands_in.items():
        if name not in BANDS:
            raise CodecError(f"bands.{name}", f"band must be one of {sorted(BANDS)}")
        if not isinstance(b, dict):
            raise CodecError(f"bands.{name}", "must be an object")
        _check_fields(b, BAND_FIELDS, f"bands.{name}.")
        k = _num(b, "k", 0, 10**6, integer=True)
        v = _array(b.get("csd"), f"bands.{name}.csd", CSD_BYTES, 9)
        p4 = _array(b.get("p4"), f"bands.{name}.p4", P4_BYTES, 3)
        if np.any(v[:, :3] < 0):
            raise CodecError(f"bands.{name}.csd", "auto-spectra must be non-negative")
        if np.any(p4 < 0):
            raise CodecError(f"bands.{name}.p4", "must be non-negative")
        bands[name] = BandFeatures(k=k, csd=unpack_csd(v), p4=p4.copy())
    meta["k"] = {n: b.k for n, b in bands.items()}

    sf = SessionFeatures(
        session_id=str(sid).lower(), building_id=bid, contributor=con,
        phone_model=meta["phone_model"], floor=meta["floor"], floor_method=meta["floor_method"],
        t_start=t_start, duration=meta["duration"], fs_raw=meta["fs_raw"], lsb=meta["lsb"],
        sync_source=meta["sync_source"], sync_sigma_ms=meta["sync_sigma_ms"],
        accept_fraction=meta["accept_fraction"], bands=bands, temp_c=meta["temp_c"],
        provenance=prov, truth=None,
    )
    return Upload(features=sf, meta=meta)


def decode(p: dict) -> SessionFeatures:
    return validate(p).features
