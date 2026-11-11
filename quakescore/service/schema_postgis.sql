-- QuakeScore production schema: Postgres 15+ with PostGIS 3 and the h3-pg extension.
-- Equivalent of quakescore/service/store.py (SQLite). NOT EXECUTED in the development environment
-- where it was written (no Postgres available there); review and test before use.

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS h3;            -- https://github.com/zachasme/h3-pg
CREATE EXTENSION IF NOT EXISTS h3_postgis;

CREATE TABLE buildings (
    id          text PRIMARY KEY,                         -- e.g. 'osm:way/123'
    footprint   geometry(MultiPolygon, 4326),             -- NULL when only a point is known
    centroid    geometry(Point, 4326) NOT NULL,
    cell        h3index NOT NULL,                         -- H3 resolution 8 of the centroid
    attrs       jsonb NOT NULL DEFAULT '{}'::jsonb,       -- storeys, height_m, year, material, use, name, address
    address_norm text GENERATED ALWAYS AS (lower(attrs->>'address')) STORED,
    updated     date NOT NULL DEFAULT current_date
);
CREATE INDEX buildings_footprint_gix ON buildings USING gist (footprint);
CREATE INDEX buildings_centroid_gix  ON buildings USING gist (centroid);
CREATE INDEX buildings_cell_ix       ON buildings (cell);
CREATE INDEX buildings_address_ix    ON buildings (address_norm);

-- Fill cell from the centroid on insert/update.
CREATE OR REPLACE FUNCTION buildings_set_cell() RETURNS trigger AS $$
BEGIN
    NEW.cell := h3_lat_lng_to_cell(NEW.centroid::point, 8);
    RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE TRIGGER buildings_cell_trg BEFORE INSERT OR UPDATE OF centroid ON buildings
    FOR EACH ROW EXECUTE FUNCTION buildings_set_cell();

-- Sessions: no IP, no location, no account. Received date only.
CREATE TABLE sessions (
    session_id   uuid PRIMARY KEY,                        -- random uuid4 from the phone; idempotency key
    building_id  text NOT NULL REFERENCES buildings(id),
    contributor  char(16) NOT NULL CHECK (contributor ~ '^[0-9a-f]{16}$'),   -- per-building pseudonym
    received     date NOT NULL DEFAULT current_date,
    floor        smallint,
    provenance   text NOT NULL CHECK (provenance IN ('REAL', 'SIM')),
    t_start      timestamptz NOT NULL CHECK (extract(second FROM t_start) = 0),   -- minute resolution
    metadata     jsonb NOT NULL,
    features_uri text NOT NULL                            -- object storage key of the gzip JSON bands
);
CREATE INDEX sessions_building_ix ON sessions (building_id);
CREATE INDEX sessions_contrib_ix  ON sessions (building_id, contributor);

-- Batch results: one record per building, unfiltered. Gating happens in the API on every read.
CREATE TABLE results (
    building_id text PRIMARY KEY REFERENCES buildings(id),
    provenance  text NOT NULL CHECK (provenance IN ('SIM', 'REAL', 'FIXTURE')),
    updated     date NOT NULL,
    record      jsonb NOT NULL,
    CONSTRAINT score_has_band CHECK (
        record->'score' IS NULL OR jsonb_typeof(record->'score') = 'null' OR
        (record->'score' ? 'value' AND record->'score' ? 'lo' AND record->'score' ? 'hi'))
);
CREATE INDEX results_status_ix ON results ((record->'coverage'->>'status'));

-- Live coverage counts per building (refresh after each batch, or make it a plain view).
CREATE MATERIALIZED VIEW building_coverage AS
SELECT building_id,
       count(*)                     AS sessions,
       count(DISTINCT contributor)  AS contributors,
       count(DISTINCT floor)        AS floors
FROM sessions GROUP BY building_id;
CREATE UNIQUE INDEX building_coverage_pk ON building_coverage (building_id);

CREATE TABLE portfolio_jobs (
    job_id   uuid PRIMARY KEY,
    created  date NOT NULL DEFAULT current_date,
    api_key_id text,                                      -- which buyer submitted it
    n_rows   integer NOT NULL,
    summary  jsonb NOT NULL,
    rows     jsonb NOT NULL
);

-- Portfolio point matching in SQL (the Python matcher does the same in development):
--   SELECT id, 0 AS distance_m FROM buildings
--    WHERE ST_Contains(footprint, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326));
--   SELECT id, ST_Distance(footprint::geography, ST_MakePoint(:lon, :lat)::geography) AS distance_m
--     FROM buildings
--    WHERE ST_DWithin(footprint::geography, ST_MakePoint(:lon, :lat)::geography, 30)
--    ORDER BY distance_m LIMIT 1;
