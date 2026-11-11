"""Small planar geometry helpers for GeoJSON footprints (no external GIS dependency).

Distances use a local equirectangular projection around the query point, which is accurate to well
under a metre at the 30 m scale used for portfolio matching.
"""
from __future__ import annotations

import math

M_PER_DEG = 111_320.0


def polygons(geom: dict) -> list[list[list[list[float]]]]:
    """List of polygons, each a list of rings of [lon, lat]."""
    if not geom:
        return []
    if geom["type"] == "Polygon":
        return [geom["coordinates"]]
    if geom["type"] == "MultiPolygon":
        return list(geom["coordinates"])
    return []


def bbox(geom: dict) -> tuple[float, float, float, float] | None:
    pts = [p for poly in polygons(geom) for ring in poly for p in ring]
    if not pts:
        if geom and geom.get("type") == "Point":
            x, y = geom["coordinates"][:2]
            return x, y, x, y
        return None
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def _ring_area_centroid(ring):
    # shift to the first vertex first: with raw lon/lat (~ -122, 37) the shoelace terms cancel
    # catastrophically for building-sized rings
    ox, oy = ring[0]
    a, cx, cy = _ring_area_centroid_local([(x - ox, y - oy) for x, y in ring])
    return a, cx + ox, cy + oy


def _ring_area_centroid_local(ring):
    a = cx = cy = 0.0
    for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1]):
        c = x0 * y1 - x1 * y0
        a += c
        cx += (x0 + x1) * c
        cy += (y0 + y1) * c
    a *= 0.5
    if abs(a) < 1e-18:
        xs = [p[0] for p in ring]
        ys = [p[1] for p in ring]
        return 0.0, sum(xs) / len(xs), sum(ys) / len(ys)
    return a, cx / (6 * a), cy / (6 * a)


def centroid(geom: dict) -> tuple[float, float]:
    """(lat, lon) area-weighted centroid of the outer rings."""
    if geom.get("type") == "Point":
        return geom["coordinates"][1], geom["coordinates"][0]
    tot = sx = sy = 0.0
    for poly in polygons(geom):
        ring = [tuple(p[:2]) for p in poly[0]]
        if len(ring) > 1 and ring[0] == ring[-1]:
            ring = ring[:-1]
        a, cx, cy = _ring_area_centroid(ring)
        w = abs(a) or 1e-18
        tot += w
        sx += cx * w
        sy += cy * w
    return sy / tot, sx / tot


def _in_ring(x: float, y: float, ring) -> bool:
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def contains(geom: dict, lat: float, lon: float) -> bool:
    for poly in polygons(geom):
        if poly and _in_ring(lon, lat, poly[0]) and not any(_in_ring(lon, lat, h) for h in poly[1:]):
            return True
    return False


def _seg_dist(px, py, ax, ay, bx, by) -> float:
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L))
    qx, qy = ax + t * dx, ay + t * dy
    return math.hypot(px - qx, py - qy)


def distance_m(geom: dict, lat: float, lon: float) -> float:
    """Distance in metres from the point to the footprint (0 inside)."""
    if geom.get("type") == "Point":
        return haversine_m(lat, lon, geom["coordinates"][1], geom["coordinates"][0])
    if contains(geom, lat, lon):
        return 0.0
    kx = M_PER_DEG * math.cos(math.radians(lat))
    ky = M_PER_DEG
    best = math.inf
    for poly in polygons(geom):
        for ring in poly:
            pts = [((p[0] - lon) * kx, (p[1] - lat) * ky) for p in ring]
            for a, b in zip(pts, pts[1:] + pts[:1]):
                best = min(best, _seg_dist(0.0, 0.0, a[0], a[1], b[0], b[1]))
    return best


def haversine_m(lat1, lon1, lat2, lon2) -> float:
    r = 6_371_008.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def expand_bbox(lat: float, lon: float, metres: float) -> tuple[float, float, float, float]:
    dlat = metres / M_PER_DEG
    dlon = metres / (M_PER_DEG * max(math.cos(math.radians(lat)), 1e-6))
    return lon - dlon, lat - dlat, lon + dlon, lat + dlat


def parse_bbox(s: str) -> tuple[float, float, float, float]:
    """'west,south,east,north' -> tuple; raises ValueError."""
    parts = [float(v) for v in s.split(",")]
    if len(parts) != 4:
        raise ValueError("bbox must be west,south,east,north")
    w, s_, e, n = parts
    if not (-180 <= w <= 180 and -180 <= e <= 180 and -90 <= s_ <= 90 and -90 <= n <= 90):
        raise ValueError("bbox out of range")
    if w > e or s_ > n:
        raise ValueError("bbox must be west,south,east,north with west<=east and south<=north")
    if not all(math.isfinite(v) for v in parts):
        raise ValueError("bbox must be finite")
    return w, s_, e, n
