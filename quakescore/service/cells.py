"""Coarse spatial cells used to hand footprints to the phone and to index buildings.

If the `h3` package (v4 API) is importable, cells are H3 resolution 8 (about 0.74 km^2).
Otherwise a documented fallback grid is used with the same function names:

  Fallback "g8" grid. Rows are bands of latitude DLAT = 0.0077 degrees (about 857 m). Within row
  iy the longitude step is DLAT / cos(latitude of the row centre), so every cell is about
  857 m x 857 m = 0.73 km^2, close to an H3 res-8 hexagon. Ids are "g8:<ix>:<iy>" with
  iy = floor(lat / DLAT) and ix = floor(lon / dlon(iy)). Cells are squares, not hexagons, and do
  not nest like H3; ids from the two systems are not interchangeable, so a database built with one
  must not be queried with the other (CELL_SYSTEM records which one is active).
"""
from __future__ import annotations

import math

try:  # pragma: no cover - depends on the environment
    import h3  # type: ignore

    _H3 = hasattr(h3, "latlng_to_cell")
except Exception:  # pragma: no cover
    h3 = None
    _H3 = False

RESOLUTION = 8
DLAT = 0.0077
CELL_SYSTEM = "h3r8" if _H3 else "g8"


def _dlon(iy: int) -> float:
    lat_c = (iy + 0.5) * DLAT
    return DLAT / max(math.cos(math.radians(lat_c)), 1e-6)


def latlng_to_cell(lat: float, lon: float) -> str:
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError("lat/lon out of range")
    if _H3:
        return h3.latlng_to_cell(lat, lon, RESOLUTION)
    iy = math.floor(lat / DLAT)
    ix = math.floor(lon / _dlon(iy))
    return f"g8:{ix}:{iy}"


def _parse(cell: str) -> tuple[int, int]:
    p = cell.split(":")
    if len(p) != 3 or p[0] != "g8":
        raise ValueError(f"not a g8 cell id: {cell!r}")
    return int(p[1]), int(p[2])


def is_valid_cell(cell: str) -> bool:
    try:
        if _H3:
            return bool(h3.is_valid_cell(cell))
        _parse(cell)
        return True
    except Exception:
        return False


def cell_to_boundary(cell: str) -> list[tuple[float, float]]:
    """Cell outline as (lat, lon) pairs."""
    if _H3:
        return [tuple(p) for p in h3.cell_to_boundary(cell)]
    ix, iy = _parse(cell)
    d = _dlon(iy)
    s, n = iy * DLAT, (iy + 1) * DLAT
    w, e = ix * d, (ix + 1) * d
    return [(s, w), (s, e), (n, e), (n, w)]


def cell_bbox(cell: str) -> tuple[float, float, float, float]:
    """(west, south, east, north) of the cell outline."""
    b = cell_to_boundary(cell)
    lats = [p[0] for p in b]
    lons = [p[1] for p in b]
    return min(lons), min(lats), max(lons), max(lats)


def grid_disk(cell: str, k: int = 1) -> list[str]:
    """The cell and its neighbours within k steps."""
    if _H3:
        return list(h3.grid_disk(cell, k))
    ix, iy = _parse(cell)
    d0 = _dlon(iy)
    lo, hi = (ix - k) * d0, (ix + 1 + k) * d0  # longitude span covered by k cells either side
    out = []
    for jy in range(iy - k, iy + k + 1):
        d = _dlon(jy)
        for jx in range(math.floor(lo / d + 1e-9), math.ceil(hi / d - 1e-9)):
            out.append(f"g8:{jx}:{jy}")
    return out


def cell_area_km2(cell: str) -> float:
    if _H3:
        return float(h3.cell_area(cell, unit="km^2"))
    w, s, e, n = cell_bbox(cell)
    lat_c = math.radians((s + n) / 2)
    return (n - s) * 111.32 * (e - w) * 111.32 * math.cos(lat_c)
