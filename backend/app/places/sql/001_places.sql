-- Places data layer (Postgres 16 + PostGIS 3). Draft for review, not applied yet.
--
-- Two layers:
--   osm_places  raw copy of OpenStreetMap. Rewritten by the import script only.
--   places      what the planner uses. Links to osm_places, adds our own fields.
-- Plus:
--   submissions business-owner form entries waiting for review.
--   import_runs one row per import, so every change can be traced to a run.

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm;   -- fuzzy name search / matching

CREATE TYPE place_status   AS ENUM ('featured', 'listed', 'hidden', 'pending');
CREATE TYPE access_status  AS ENUM ('yes', 'limited', 'no', 'unknown');
CREATE TYPE place_source   AS ENUM ('osm', 'owner', 'curated');
CREATE TYPE submission_state AS ENUM ('new', 'matched', 'approved', 'rejected');

-- ---------------------------------------------------------------------------
-- Import bookkeeping
-- ---------------------------------------------------------------------------
CREATE TABLE import_runs (
    id            bigserial PRIMARY KEY,
    region        text        NOT NULL,              -- 'calamba'
    source_file   text        NOT NULL,              -- e.g. philippines-latest.osm.pbf
    source_date   timestamptz NOT NULL,              -- OSM data timestamp from the file
    started_at    timestamptz NOT NULL DEFAULT now(),
    finished_at   timestamptz,
    added         int NOT NULL DEFAULT 0,
    updated       int NOT NULL DEFAULT 0,
    missing       int NOT NULL DEFAULT 0             -- were in OSM before, gone now
);

-- ---------------------------------------------------------------------------
-- Layer 1: raw OSM (never edited by hand)
-- ---------------------------------------------------------------------------
CREATE TABLE osm_places (
    osm_ref       text PRIMARY KEY CHECK (osm_ref ~ '^(node|way|relation)/[0-9]+$'),
    region        text        NOT NULL,
    name          text        NOT NULL,
    osm_key       text        NOT NULL,              -- amenity / tourism / leisure / shop / historic / natural
    osm_value     text        NOT NULL,              -- restaurant / museum / water_park ...
    geom          geography(Point, 4326) NOT NULL,   -- centroid for ways/relations
    tags          jsonb       NOT NULL,              -- full tag set, for later use
    first_seen_run bigint     NOT NULL REFERENCES import_runs(id),
    last_seen_run  bigint     NOT NULL REFERENCES import_runs(id)
);
CREATE INDEX osm_places_geom_idx   ON osm_places USING gist (geom);
CREATE INDEX osm_places_region_idx ON osm_places (region, last_seen_run);

-- ---------------------------------------------------------------------------
-- Layer 2: what the planner uses
-- ---------------------------------------------------------------------------
CREATE TABLE places (
    id              text PRIMARY KEY CHECK (id ~ '^(osm:(node|way|relation)/[0-9]+|curated:[a-z0-9-]{1,64})$'),
    osm_ref         text UNIQUE REFERENCES osm_places(osm_ref) ON DELETE SET NULL,
    region          text        NOT NULL,
    name            text        NOT NULL,
    category        text        NOT NULL,            -- Interest value, 'landmark' or 'other'
    kind            text        NOT NULL,            -- finer type: 'restaurant', 'water_park' ...
    geom            geography(Point, 4326) NOT NULL,
    barangay        text,
    outdoor         boolean     NOT NULL DEFAULT false,
    is_chain        boolean     NOT NULL DEFAULT false,
    status          place_status NOT NULL DEFAULT 'pending',
    status_reason   text,                            -- which rule set the status, or 'alli'
    wheelchair      access_status NOT NULL DEFAULT 'unknown',
    opening_hours   text,                            -- OSM opening_hours syntax
    hours_verified  boolean     NOT NULL DEFAULT false,
    price_tier      text CHECK (price_tier IN ('budget', 'mid', 'premium')),
    website         text,
    -- Fields a person changed by hand. An OSM refresh never overwrites these.
    -- e.g. {"opening_hours": "owner", "name": "alli"}
    overrides       jsonb       NOT NULL DEFAULT '{}'::jsonb,
    possibly_closed boolean     NOT NULL DEFAULT false,  -- vanished from OSM, needs a check
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX places_geom_idx          ON places USING gist (geom);
-- Planner reads only usable places of one region; keep that path small and fast.
CREATE INDEX places_region_usable_idx ON places (region, category)
    WHERE status IN ('featured', 'listed') AND NOT possibly_closed;
CREATE INDEX places_name_trgm_idx     ON places USING gin (name gin_trgm_ops);

-- ---------------------------------------------------------------------------
-- Business-owner submissions
-- ---------------------------------------------------------------------------
CREATE TABLE submissions (
    id              bigserial PRIMARY KEY,
    region          text        NOT NULL,
    business_name   text        NOT NULL,
    category        text        NOT NULL,
    geom            geography(Point, 4326) NOT NULL,
    opening_hours   text,
    wheelchair      access_status NOT NULL DEFAULT 'unknown',
    website         text,
    contact_email   text        NOT NULL,            -- private; never shown publicly
    state           submission_state NOT NULL DEFAULT 'new',
    matched_place_id text REFERENCES places(id),     -- set when it matches an existing place
    match_score     real,
    reviewed_by     text,
    reviewed_at     timestamptz,
    created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX submissions_state_idx ON submissions (state, created_at);
CREATE INDEX submissions_geom_idx  ON submissions USING gist (geom);

-- ---------------------------------------------------------------------------
-- Typical planner query: usable places within 3 km of a point
-- ---------------------------------------------------------------------------
-- SELECT id, name, category
-- FROM places
-- WHERE region = 'calamba'
--   AND status IN ('featured', 'listed') AND NOT possibly_closed
--   AND ST_DWithin(geom, ST_MakePoint(:lng, :lat)::geography, 3000);
