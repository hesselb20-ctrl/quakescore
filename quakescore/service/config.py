"""Service configuration, read from environment variables at call time (so tests can override).

QS_DB              SQLite path (default <repo>/data/quakescore.sqlite)
QS_BLOB_DIR        unused unless set: store session feature blobs as files instead of BLOBs
QS_K_CONTRIBUTORS  minimum distinct contributors before release (default 3)
QS_K_SESSIONS      minimum sessions before release (default 5)
QS_API_KEYS        comma-separated buyer API keys. PLACEHOLDER mechanism: a static key list is not
                   production authentication. Default "demo-key" is for local development only.
QS_CORS_ORIGINS    comma-separated allowed origins for the dashboard (default "*")
QS_INSPECTION_URL  where the resident card points for an inspection route
QS_MAX_UPLOAD_MB   maximum (compressed) upload size, default 2
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEFAULT_DB = REPO / "data" / "quakescore.sqlite"
DEFAULT_INSPECTION_URL = "docs/responsible_use.md"


@dataclass(frozen=True)
class Config:
    db_path: str
    blob_dir: str | None
    k_contributors: int
    k_sessions: int
    api_keys: tuple[str, ...]
    cors_origins: tuple[str, ...]
    inspection_url: str
    max_upload_bytes: int


def get_config() -> Config:
    env = os.environ
    return Config(
        db_path=env.get("QS_DB", str(DEFAULT_DB)),
        blob_dir=env.get("QS_BLOB_DIR") or None,
        k_contributors=int(env.get("QS_K_CONTRIBUTORS", "3")),
        k_sessions=int(env.get("QS_K_SESSIONS", "5")),
        api_keys=tuple(k.strip() for k in env.get("QS_API_KEYS", "demo-key").split(",") if k.strip()),
        cors_origins=tuple(o.strip() for o in env.get("QS_CORS_ORIGINS", "*").split(",") if o.strip()),
        inspection_url=env.get("QS_INSPECTION_URL", DEFAULT_INSPECTION_URL),
        max_upload_bytes=int(float(env.get("QS_MAX_UPLOAD_MB", "2")) * 1024 * 1024),
    )
