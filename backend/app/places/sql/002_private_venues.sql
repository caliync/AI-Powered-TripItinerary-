-- Private venues (Postgres plan). Draft for review, not applied yet.
--
-- Alli 2026-11-18: plans use walk-in public places only. Resorts that take
-- walk-in guests are ordinary places. Resorts that are rented whole or need
-- booking (or have no walk-in evidence yet) live here and are never planned.

CREATE TYPE partnership_status AS ENUM ('none', 'contacted', 'partner');
CREATE TYPE walk_in_status AS ENUM ('no', 'unknown');  -- 'yes' rows belong in places

CREATE TABLE private_venues (
    id              text PRIMARY KEY CHECK (id ~ '^(osm:(node|way|relation)/[0-9]+|curated:[a-z0-9-]{1,64})$'),
    osm_ref         text UNIQUE REFERENCES osm_places(osm_ref) ON DELETE SET NULL,
    region          text        NOT NULL,
    name            text        NOT NULL,
    kind            text        NOT NULL,            -- 'water_park', 'resort', 'swimming_pool', 'curated'
    geom            geography(Point, 4326) NOT NULL,
    wheelchair      access_status NOT NULL DEFAULT 'unknown',
    opening_hours   text,
    website         text,
    details         text,
    walk_in         walk_in_status NOT NULL DEFAULT 'unknown',
    walk_in_reason  text,                            -- the rule that decided, e.g. 'rule:private_name'
    partnership     partnership_status NOT NULL DEFAULT 'none',
    partnership_notes text,
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX private_venues_geom_idx ON private_venues USING gist (geom);
-- Used to find the traveller's stay by name (many stay at a resort).
CREATE INDEX private_venues_name_trgm ON private_venues USING gin (name gin_trgm_ops);
