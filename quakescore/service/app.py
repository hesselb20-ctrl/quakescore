"""QuakeScore API (FastAPI), versioned under /v1.

    uvicorn quakescore.service.app:app --no-access-log

Run with --no-access-log: the default access log writes client IP addresses and query strings, and
this service never stores IP addresses or location.

Public (phone app, residents): POST /v1/sessions, GET /v1/footprints, GET /v1/coverage,
GET /v1/buildings/{id}/public, GET /v1/contributors/{pseudonym}/badges, GET /v1/meta.
Buyer (X-API-Key header): GET /v1/buildings, GET /v1/buildings/{id}, POST /v1/portfolio,
GET /v1/portfolio/{job_id}, GET /v1/export.csv, GET /v1/export.geojson.

The API key check is a PLACEHOLDER (a static key list from QS_API_KEYS), not production auth.
"""
from __future__ import annotations

import json
import re
import uuid
import zlib

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse, Response

from quakescore.service import cells, codec, portfolio, views
from quakescore.service.config import Config, get_config
from quakescore.service.coverage import badges, public_card
from quakescore.service.geo import parse_bbox
from quakescore.service.store import Store, open_store

MAX_DECOMPRESSED = 8 * 1024 * 1024
FOOTPRINT_BOX_DEG = 0.01        # lat/lon form returns every footprint within +-0.01 degrees
PSEUDONYM_RE = re.compile(r"^[0-9a-f]{16}$")
STATUS_VALUES = {"scored", "needs_data", "no_data"}


def _reject_constant(c):
    raise ValueError(f"non-finite number {c} not allowed")


class PrivacyScrubMiddleware:
    """Pure ASGI middleware: when the response starts, blank the request's query string and client
    address in the ASGI scope. Server access loggers (uvicorn) read both from the scope when the
    response starts, so even if --no-access-log is forgotten they log neither the coordinates of
    GET /v1/footprints?lat=&lon= nor the caller's IP. The application itself never logs requests."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            return await self.app(scope, receive, send)

        async def scrubbed_send(message):
            if message.get("type") == "http.response.start":
                scope["query_string"] = b""
                scope["client"] = None
                if scope.get("path", "").startswith("/v1/sessions/"):   # session id is a capability
                    scope["path"] = "/v1/sessions/{session_id}"
                    scope["raw_path"] = b"/v1/sessions/{session_id}"
            await send(message)

        await self.app(scope, receive, scrubbed_send)


def create_app(store: Store | None = None, cfg: Config | None = None) -> FastAPI:
    app = FastAPI(title="QuakeScore API", version="1.0.0",
                  description="Statistical seismic screening layer. Not a structural engineering "
                              "assessment. Buyer endpoints need X-API-Key (placeholder auth).")
    state = {"store": store, "cfg": cfg}

    def get_cfg() -> Config:
        if state["cfg"] is None:
            state["cfg"] = get_config()
        return state["cfg"]

    def get_store() -> Store:
        if state["store"] is None:
            state["store"] = open_store(get_cfg())
        return state["store"]

    app.add_middleware(CORSMiddleware, allow_origins=list(get_cfg().cors_origins),
                       allow_methods=["GET", "POST", "DELETE"], allow_headers=["X-API-Key", "Content-Type",
                                                                     "Content-Encoding"])

    app.add_middleware(PrivacyScrubMiddleware)   # added last = outermost

    def buyer(request: Request, cfg: Config = Depends(get_cfg)):
        key = request.headers.get("x-api-key")
        if not key or key not in cfg.api_keys:
            raise HTTPException(401, "buyer endpoint: missing or invalid X-API-Key")
        return key

    # ------------------------------------------------------------------ sessions (phone upload)
    @app.post("/v1/sessions", status_code=201)
    async def post_session(request: Request, st: Store = Depends(get_store),
                           cfg: Config = Depends(get_cfg)):
        body = await request.body()
        if len(body) > cfg.max_upload_bytes:
            raise HTTPException(413, "upload too large")
        if request.headers.get("content-encoding", "").lower() == "gzip" or body[:2] == b"\x1f\x8b":
            d = zlib.decompressobj(wbits=16 + zlib.MAX_WBITS)
            try:
                raw = d.decompress(body, MAX_DECOMPRESSED)
            except zlib.error:
                raise HTTPException(400, "invalid gzip body") from None
            if d.unconsumed_tail:
                raise HTTPException(413, "decompressed upload too large")
        else:
            raw = body
        try:
            payload = json.loads(raw, parse_constant=_reject_constant)
        except (ValueError, UnicodeDecodeError):
            raise HTTPException(400, "body must be JSON (optionally gzip-compressed)") from None
        try:
            up = codec.validate(payload)
        except codec.CodecError as e:
            raise HTTPException(422, {"field": e.field, "error": e.msg}) from None
        sf = up.features
        if st.has_session(sf.session_id):
            return JSONResponse({"status": "duplicate", "session_id": sf.session_id}, status_code=200)
        if st.get_building(sf.building_id) is None:
            raise HTTPException(422, {"field": "building_id", "error": "unknown building id"})
        inserted = st.add_session(sf.session_id, sf.building_id, sf.contributor, up.meta,
                                  payload["bands"])
        if not inserted:  # lost a race with an identical upload
            return JSONResponse({"status": "duplicate", "session_id": sf.session_id}, status_code=200)
        return {"status": "stored", "session_id": sf.session_id}

    @app.delete("/v1/sessions/{session_id}", status_code=204)
    def delete_session(session_id: str, st: Store = Depends(get_store)):
        """Contributor deletes one of their own sessions. The random session id is the capability.
        Always 204 (whether or not the id existed) so ids cannot be probed."""
        try:
            sid = str(uuid.UUID(session_id))
        except ValueError:
            raise HTTPException(422, "session_id must be a uuid") from None
        st.delete_session(sid)
        return Response(status_code=204)

    # ------------------------------------------------------------------ footprints (phone snap)
    @app.get("/v1/footprints")
    def get_footprints(cell: str | None = None, lat: float | None = None, lon: float | None = None,
                       ring: int = Query(0, ge=0, le=1), st: Store = Depends(get_store)):
        if cell is None:
            if lat is None or lon is None:
                raise HTTPException(422, "give cell=<id> or lat= and lon=")
            # The app sends lat/lon rounded to 0.01 degrees. Return every footprint whose outline
            # intersects the +-0.01 degree box around the point. The point is not stored or logged.
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                raise HTTPException(422, "lat/lon out of range")
            d = FOOTPRINT_BOX_DEG
            bl = st.buildings_in_bbox(lon - d - 1e-9, lat - d - 1e-9, lon + d + 1e-9, lat + d + 1e-9)
            feats = [{"type": "Feature", "id": b["id"], "geometry": views.geometry(b),
                      "properties": {"id": b["id"], "name": b["attrs"].get("name"),
                                     "address": b["attrs"].get("address"),
                                     "storeys": b["attrs"].get("storeys")}} for b in bl]
            return {"type": "FeatureCollection", "box_deg": d, "features": feats}
        if not cells.is_valid_cell(cell):
            raise HTTPException(422, f"invalid cell id for cell system {cells.CELL_SYSTEM}")
        ids = cells.grid_disk(cell, ring) if ring else [cell]
        feats = [{"type": "Feature", "id": b["id"], "geometry": views.geometry(b),
                  "properties": {"id": b["id"], "name": b["attrs"].get("name"),
                                 "address": b["attrs"].get("address"),
                                 "storeys": b["attrs"].get("storeys")}}
                 for b in st.buildings_in_cells(ids)]
        return {"type": "FeatureCollection", "cell": cell, "cells": ids,
                "cell_system": cells.CELL_SYSTEM, "features": feats}

    # ------------------------------------------------------------------ public building card
    @app.get("/v1/buildings/{building_id:path}/public")
    def get_public(building_id: str, st: Store = Depends(get_store), cfg: Config = Depends(get_cfg)):
        v = views.view_one(st, building_id, cfg)
        if v is None:
            raise HTTPException(404, "unknown building")
        return public_card(v, cfg)

    # ------------------------------------------------------------------ buyer: buildings
    @app.get("/v1/buildings", dependencies=[Depends(buyer)])
    def list_buildings(bbox: str | None = None, min_score: float | None = None,
                       max_score: float | None = None, status: str | None = None,
                       provenance: str | None = None, limit: int = Query(1000, ge=1, le=20000),
                       st: Store = Depends(get_store), cfg: Config = Depends(get_cfg)):
        if status is not None and status not in STATUS_VALUES:
            raise HTTPException(422, f"status must be one of {sorted(STATUS_VALUES)}")
        try:
            bl = st.buildings_in_bbox(*parse_bbox(bbox)) if bbox else st.all_buildings()
        except ValueError as e:
            raise HTTPException(422, str(e)) from None
        out = []
        for b, v in views.views_for(st, bl, cfg):
            if status and v["coverage"]["status"] != status:
                continue
            if provenance and v["provenance"] != provenance:
                continue
            if min_score is not None or max_score is not None:
                if not v["released"]:
                    continue
                s = v["score"]["value"]
                if (min_score is not None and s < min_score) or (max_score is not None and s > max_score):
                    continue
            out.append((b, v))
            if len(out) >= limit:
                break
        return views.collection(out, {"count": len(out), "k_threshold":
                                      {"contributors": cfg.k_contributors, "sessions": cfg.k_sessions}})

    @app.get("/v1/buildings/{building_id:path}", dependencies=[Depends(buyer)])
    def get_building(building_id: str, st: Store = Depends(get_store), cfg: Config = Depends(get_cfg)):
        v = views.view_one(st, building_id, cfg)
        if v is None:
            raise HTTPException(404, "unknown building")
        return v

    # ------------------------------------------------------------------ public coverage
    @app.get("/v1/coverage")
    def get_coverage(bbox: str | None = None, st: Store = Depends(get_store),
                     cfg: Config = Depends(get_cfg)):
        try:
            bl = st.buildings_in_bbox(*parse_bbox(bbox)) if bbox else st.all_buildings()
        except ValueError as e:
            raise HTTPException(422, str(e)) from None
        feats = []
        counts = {"scored": 0, "needs_data": 0, "no_data": 0}
        for b, v in views.views_for(st, bl, cfg):
            c = v["coverage"]
            counts[c["status"]] += 1
            feats.append({"type": "Feature", "id": b["id"], "geometry": views.geometry(b),
                          "properties": {"id": b["id"], "status": c["status"], "sessions": c["sessions"],
                                         "contributors": c["contributors"], "floors": c["floors"],
                                         "sessions_needed": c["sessions_needed"],
                                         "contributors_needed": c["contributors_needed"],
                                         "provenance": v["provenance"]}})
        return {"type": "FeatureCollection", "features": feats,
                "meta": {"counts": counts, "k_threshold": {"contributors": cfg.k_contributors,
                                                           "sessions": cfg.k_sessions}}}

    # ------------------------------------------------------------------ buyer: portfolio
    @app.post("/v1/portfolio", dependencies=[Depends(buyer)])
    async def post_portfolio(request: Request, st: Store = Depends(get_store),
                             cfg: Config = Depends(get_cfg)):
        ctype = request.headers.get("content-type", "")
        if ctype.startswith("multipart/form-data"):
            form = await request.form()
            f = form.get("file")
            if f is None or isinstance(f, str):
                raise HTTPException(422, "multipart upload needs a 'file' field with the CSV")
            data = await f.read()
        else:
            data = await request.body()
        if len(data) > 5 * 1024 * 1024:
            raise HTTPException(413, "CSV larger than 5 MB")
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise HTTPException(422, "CSV must be UTF-8") from None
        try:
            res = portfolio.run(st, cfg, text)
        except ValueError as e:
            raise HTTPException(422, str(e)) from None
        res["job_id"] = st.put_job(res["summary"], res["rows"])
        return res

    @app.get("/v1/portfolio/{job_id}", dependencies=[Depends(buyer)])
    def get_portfolio(job_id: str, st: Store = Depends(get_store)):
        j = st.get_job(job_id)
        if j is None:
            raise HTTPException(404, "unknown job")
        return j

    # ------------------------------------------------------------------ buyer: exports
    @app.get("/v1/export.csv", dependencies=[Depends(buyer)])
    def export_csv(st: Store = Depends(get_store), cfg: Config = Depends(get_cfg)):
        vs = [v for _, v in views.views_for(st, st.all_buildings(), cfg)]
        return PlainTextResponse(views.export_csv(vs), media_type="text/csv",
                                 headers={"Content-Disposition": 'attachment; filename="quakescore.csv"'})

    @app.get("/v1/export.geojson", dependencies=[Depends(buyer)])
    def export_geojson(st: Store = Depends(get_store), cfg: Config = Depends(get_cfg)):
        pairs = [(b, v) for b, v in views.views_for(st, st.all_buildings(), cfg) if v["released"]]
        fc = {"type": "FeatureCollection",
              "features": [{"type": "Feature", "id": v["building_id"], "geometry": views.geometry(b),
                            "properties": views.export_row(v)} for b, v in pairs],
              "meta": {"count": len(pairs), "licence": "Footprints (c) OpenStreetMap contributors, ODbL"}}
        return JSONResponse(fc, headers={"Content-Disposition":
                                         'attachment; filename="quakescore.geojson"'})

    # ------------------------------------------------------------------ public: badges
    @app.get("/v1/contributors/{pseudonym}/badges")
    def get_badges(pseudonym: str, building_id: str, st: Store = Depends(get_store),
                   cfg: Config = Depends(get_cfg)):
        if not PSEUDONYM_RE.match(pseudonym):
            raise HTTPException(422, "pseudonym must be 16 lowercase hex characters")
        if st.get_building(building_id) is None:
            raise HTTPException(404, "unknown building")
        return badges(pseudonym, st.session_rows(building_id), cfg)

    # ------------------------------------------------------------------ public: meta
    @app.get("/v1/meta")
    def get_meta(st: Store = Depends(get_store), cfg: Config = Depends(get_cfg)):
        provs: dict[str, int] = {}
        for r in st.all_results().values():
            provs[r["provenance"]] = provs.get(r["provenance"], 0) + 1
        return {"api_version": "v1", "buildings": st.count_buildings(), "sessions": st.count_sessions(),
                "result_provenance": provs, "cell_system": cells.CELL_SYSTEM,
                "footprints_synthetic": st.get_meta("footprints_synthetic") == "1",
                "k_threshold": {"contributors": cfg.k_contributors, "sessions": cfg.k_sessions},
                "auth": "placeholder static API keys (QS_API_KEYS)"}

    return app


app = create_app()
