"""SQLite storage for local development and tests (stdlib sqlite3).

The production equivalent (Postgres + PostGIS + H3) is schema_postgis.sql. Spatial queries here use a
bounding-box index plus exact tests in Python (geo.py); that is adequate for a city-sized demo.

What is stored for a session: random session id, building id, the per-building contributor
pseudonym, the date it was received (date only, no time), the validated metadata, and the spectral
features as a compressed blob. No IP address, no location and no account is ever stored: the
upload codec refuses location fields and the API never passes request metadata to this module.
"""
from __future__ import annotations

import gzip
import json
import sqlite3
import threading
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

from quakescore.service import cells, geo

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS buildings (
    id         TEXT PRIMARY KEY,
    footprint  TEXT,              -- GeoJSON geometry (Polygon / MultiPolygon), NULL if unknown
    lat        REAL NOT NULL,     -- centroid
    lon        REAL NOT NULL,
    cell       TEXT NOT NULL,     -- cells.latlng_to_cell(lat, lon); see cells.CELL_SYSTEM
    minx REAL, miny REAL, maxx REAL, maxy REAL,
    attrs      TEXT NOT NULL      -- JSON: storeys, height_m, year, material, use, name, address, ...
);
CREATE INDEX IF NOT EXISTS buildings_cell ON buildings(cell);
CREATE INDEX IF NOT EXISTS buildings_bbox ON buildings(minx, maxx, miny, maxy);

CREATE TABLE IF NOT EXISTS sessions (
    session_id  TEXT PRIMARY KEY,
    building_id TEXT NOT NULL,
    contributor TEXT NOT NULL,    -- pseudonym, salted per building on the phone
    received    TEXT NOT NULL,    -- ISO date only
    floor       INTEGER,
    provenance  TEXT NOT NULL,
    t_start     REAL NOT NULL,    -- rounded to the minute by the phone
    metadata    TEXT NOT NULL,    -- validated scalar fields (JSON)
    features    BLOB,             -- gzip JSON of the encoded bands, or NULL when stored as a file
    features_path TEXT            -- file path when QS_BLOB_DIR is set
);
CREATE INDEX IF NOT EXISTS sessions_building ON sessions(building_id);
CREATE INDEX IF NOT EXISTS sessions_contributor ON sessions(building_id, contributor);

CREATE TABLE IF NOT EXISTS results (
    building_id TEXT PRIMARY KEY,
    provenance  TEXT NOT NULL,
    updated     TEXT NOT NULL,
    record      TEXT NOT NULL     -- the batch job's record (JSON), unfiltered; gating happens on read
);

CREATE TABLE IF NOT EXISTS portfolio_jobs (
    job_id   TEXT PRIMARY KEY,
    created  TEXT NOT NULL,       -- ISO date
    n_rows   INTEGER NOT NULL,
    summary  TEXT NOT NULL,       -- JSON
    rows     TEXT NOT NULL        -- JSON list of per-row results
);

-- buildings whose stored result must be recomputed (e.g. a contributor deleted a session)
CREATE TABLE IF NOT EXISTS recompute (
    building_id TEXT PRIMARY KEY,
    since       TEXT NOT NULL     -- ISO date
);

CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
"""


class Store:
    def __init__(self, path: str, blob_dir: str | None = None):
        self.path = path
        self.blob_dir = blob_dir
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA_SQL)
        cur = self.get_meta("cell_system")
        if cur is None:
            self.set_meta("cell_system", cells.CELL_SYSTEM)
        elif cur != cells.CELL_SYSTEM:
            raise RuntimeError(f"database was built with cell system {cur!r}, but {cells.CELL_SYSTEM!r} "
                               "is active; rebuild the database (load_footprints) to switch")

    def close(self):
        self.db.close()

    # -- meta ------------------------------------------------------------------------------
    def get_meta(self, key: str) -> str | None:
        r = self.db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return r[0] if r else None

    def set_meta(self, key: str, value: str):
        with self._lock, self.db:
            self.db.execute("INSERT OR REPLACE INTO meta VALUES (?,?)", (key, value))

    # -- buildings -------------------------------------------------------------------------
    def upsert_building(self, bid: str, footprint: dict | None, attrs: dict,
                        lat: float | None = None, lon: float | None = None):
        if footprint:
            lat, lon = geo.centroid(footprint)
            bb = geo.bbox(footprint)
        else:
            if lat is None or lon is None:
                raise ValueError(f"{bid}: need a footprint or lat/lon")
            bb = (lon, lat, lon, lat)
        with self._lock, self.db:
            self.db.execute(
                "INSERT OR REPLACE INTO buildings VALUES (?,?,?,?,?,?,?,?,?,?)",
                (bid, json.dumps(footprint) if footprint else None, lat, lon,
                 cells.latlng_to_cell(lat, lon), *bb, json.dumps(attrs)))

    @staticmethod
    def _b(row) -> dict:
        return {"id": row["id"], "footprint": json.loads(row["footprint"]) if row["footprint"] else None,
                "lat": row["lat"], "lon": row["lon"], "cell": row["cell"],
                "attrs": json.loads(row["attrs"])}

    def get_building(self, bid: str) -> dict | None:
        r = self.db.execute("SELECT * FROM buildings WHERE id=?", (bid,)).fetchone()
        return self._b(r) if r else None

    def buildings_in_cells(self, cell_ids: list[str]) -> list[dict]:
        if not cell_ids:
            return []
        q = ",".join("?" * len(cell_ids))
        return [self._b(r) for r in
                self.db.execute(f"SELECT * FROM buildings WHERE cell IN ({q}) ORDER BY id", cell_ids)]

    def buildings_in_bbox(self, w: float, s: float, e: float, n: float) -> list[dict]:
        rows = self.db.execute(
            "SELECT * FROM buildings WHERE maxx>=? AND minx<=? AND maxy>=? AND miny<=? ORDER BY id",
            (w, e, s, n))
        return [self._b(r) for r in rows]

    def all_buildings(self) -> list[dict]:
        return [self._b(r) for r in self.db.execute("SELECT * FROM buildings ORDER BY id")]

    def count_buildings(self) -> int:
        return self.db.execute("SELECT COUNT(*) FROM buildings").fetchone()[0]

    # -- sessions --------------------------------------------------------------------------
    def has_session(self, session_id: str) -> bool:
        return self.db.execute("SELECT 1 FROM sessions WHERE session_id=?",
                               (session_id,)).fetchone() is not None

    def add_session(self, session_id: str, building_id: str, contributor: str, meta: dict,
                    bands_encoded: dict, received: date | None = None) -> bool:
        """Insert a session. Returns False (and changes nothing) if session_id already exists."""
        blob = gzip.compress(json.dumps(bands_encoded, separators=(",", ":")).encode(), 6)
        received = (received or datetime.now(timezone.utc).date()).isoformat()
        path = None
        if self.blob_dir:
            p = Path(self.blob_dir) / f"{session_id}.json.gz"
            p.parent.mkdir(parents=True, exist_ok=True)
            path = str(p)
        with self._lock, self.db:
            cur = self.db.execute(
                "INSERT OR IGNORE INTO sessions VALUES (?,?,?,?,?,?,?,?,?,?)",
                (session_id, building_id, contributor, received, meta.get("floor"),
                 meta.get("provenance", "REAL"), meta["t_start"], json.dumps(meta),
                 None if path else blob, path))
            inserted = cur.rowcount == 1
        if inserted and path:
            Path(path).write_bytes(blob)
        return inserted

    def session_payload(self, session_id: str) -> dict | None:
        """Rebuild the schema-1 payload (for re-decoding with codec.decode)."""
        r = self.db.execute("SELECT * FROM sessions WHERE session_id=?", (session_id,)).fetchone()
        if not r:
            return None
        blob = r["features"] if r["features"] is not None else Path(r["features_path"]).read_bytes()
        meta = json.loads(r["metadata"])
        p = {k: v for k, v in meta.items() if k not in ("k",)}
        if p.get("provenance") == "REAL":
            p.pop("provenance")
        p.update(session_id=r["session_id"], building_id=r["building_id"],
                 contributor=r["contributor"], bands=json.loads(gzip.decompress(blob)))
        return p

    def delete_session(self, session_id: str) -> bool:
        """Remove a session and its features. Marks the building for recomputation.
        Returns True if something was deleted (the API does not reveal this)."""
        with self._lock, self.db:
            r = self.db.execute("SELECT building_id, features_path FROM sessions WHERE session_id=?",
                                (session_id,)).fetchone()
            if not r:
                return False
            self.db.execute("DELETE FROM sessions WHERE session_id=?", (session_id,))
            self.db.execute("INSERT OR REPLACE INTO recompute VALUES (?,?)",
                            (r["building_id"], datetime.now(timezone.utc).date().isoformat()))
        if r["features_path"]:
            Path(r["features_path"]).unlink(missing_ok=True)
        return True

    def needs_recompute(self, building_id: str) -> bool:
        return self.db.execute("SELECT 1 FROM recompute WHERE building_id=?",
                               (building_id,)).fetchone() is not None

    def recompute_ids(self) -> set[str]:
        return {r[0] for r in self.db.execute("SELECT building_id FROM recompute")}

    def session_rows(self, building_id: str) -> list[dict]:
        """Lightweight rows (no features) for coverage and badges."""
        rows = self.db.execute(
            "SELECT session_id, contributor, floor, t_start, provenance FROM sessions "
            "WHERE building_id=? ORDER BY t_start, session_id", (building_id,))
        return [dict(r) for r in rows]

    def session_counts(self) -> dict[str, dict]:
        out = {}
        for r in self.db.execute(
                "SELECT building_id, COUNT(*) s, COUNT(DISTINCT contributor) c, "
                "COUNT(DISTINCT floor) f FROM sessions GROUP BY building_id"):
            out[r["building_id"]] = {"sessions": r["s"], "contributors": r["c"], "floors": r["f"]}
        return out

    def count_sessions(self) -> int:
        return self.db.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]

    # -- results ---------------------------------------------------------------------------
    def put_result(self, rec: dict):
        """Store a batch record; a fresh record clears the building's recompute mark."""
        with self._lock, self.db:
            self.db.execute("INSERT OR REPLACE INTO results VALUES (?,?,?,?)",
                            (rec["building_id"], rec["provenance"], rec["updated"], json.dumps(rec)))
            self.db.execute("DELETE FROM recompute WHERE building_id=?", (rec["building_id"],))

    def clear_results(self):
        with self._lock, self.db:
            self.db.execute("DELETE FROM results")

    def get_result(self, bid: str) -> dict | None:
        r = self.db.execute("SELECT record FROM results WHERE building_id=?", (bid,)).fetchone()
        return json.loads(r[0]) if r else None

    def results_for(self, ids: list[str]) -> dict[str, dict]:
        out = {}
        for i in range(0, len(ids), 500):
            chunk = ids[i:i + 500]
            q = ",".join("?" * len(chunk))
            for r in self.db.execute(f"SELECT building_id, record FROM results WHERE building_id IN ({q})",
                                     chunk):
                out[r[0]] = json.loads(r[1])
        return out

    def all_results(self) -> dict[str, dict]:
        return {r[0]: json.loads(r[1]) for r in self.db.execute("SELECT building_id, record FROM results")}

    # -- portfolio jobs --------------------------------------------------------------------
    def put_job(self, summary: dict, rows: list[dict]) -> str:
        job_id = str(uuid.uuid4())
        with self._lock, self.db:
            self.db.execute("INSERT INTO portfolio_jobs VALUES (?,?,?,?,?)",
                            (job_id, datetime.now(timezone.utc).date().isoformat(), len(rows),
                             json.dumps(summary), json.dumps(rows)))
        return job_id

    def get_job(self, job_id: str) -> dict | None:
        r = self.db.execute("SELECT * FROM portfolio_jobs WHERE job_id=?", (job_id,)).fetchone()
        if not r:
            return None
        return {"job_id": r["job_id"], "created": r["created"], "n_rows": r["n_rows"],
                "summary": json.loads(r["summary"]), "rows": json.loads(r["rows"])}


def open_store(cfg=None) -> Store:
    from quakescore.service.config import get_config
    cfg = cfg or get_config()
    return Store(cfg.db_path, cfg.blob_dir)
