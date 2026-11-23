"""SQLite storage for beta. Same tables as the Postgres plan, minus PostGIS.

Records are stored as Pydantic JSON, so the models stay the single source of
truth. Columns outside the JSON exist only for lookups.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from .places.models import PlaceRecord, PrivateVenue, Submission
from .schema import Itinerary, RegionId

SCHEMA = """
CREATE TABLE IF NOT EXISTS places (
    id TEXT PRIMARY KEY,
    region TEXT NOT NULL,
    status TEXT NOT NULL,
    data TEXT NOT NULL,
    details TEXT
);
CREATE INDEX IF NOT EXISTS places_region_status ON places (region, status);
-- Resorts and pools with no walk-in evidence: kept out of plans until a partnership exists.
CREATE TABLE IF NOT EXISTS private_venues (
    id TEXT PRIMARY KEY,
    region TEXT NOT NULL,
    partnership TEXT NOT NULL DEFAULT 'none',
    data TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS itineraries (
    id TEXT PRIMARY KEY,
    version INTEGER NOT NULL,
    data TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data TEXT NOT NULL,
    matched_place_id TEXT,
    match_score REAL,
    review_status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL
);
"""


class StaleVersion(Exception):
    """Someone saved the itinerary since the client loaded it."""


def _now() -> str:
    return datetime.now(UTC).isoformat()


class Store:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as c:
            c.executescript(SCHEMA)

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.path)
        try:
            with conn:  # commits, or rolls back on error
                yield conn
        finally:
            conn.close()

    # ---------------- places ----------------
    def place_count(self) -> int:
        with self._conn() as c:
            return c.execute("SELECT count(*) FROM places").fetchone()[0]

    def upsert_places(self, places: list[PlaceRecord], details: dict[str, str]) -> None:
        rows = [(p.id, p.region.value, p.status.value, p.model_dump_json(), details.get(p.id)) for p in places]
        with self._conn() as c:
            c.executemany(
                "INSERT INTO places (id, region, status, data, details) VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET region=excluded.region, status=excluded.status, "
                "data=excluded.data, details=excluded.details",
                rows,
            )

    def places(self, region: RegionId) -> tuple[list[PlaceRecord], dict[str, str]]:
        with self._conn() as c:
            rows = c.execute("SELECT data, details FROM places WHERE region = ?", (region.value,)).fetchall()
        places = [PlaceRecord.model_validate_json(r[0]) for r in rows]
        details = {p.id: r[1] for p, r in zip(places, rows) if r[1]}
        return places, details

    # ---------------- private venues ----------------
    def upsert_venues(self, venues: list[PrivateVenue]) -> None:
        rows = [(v.id, v.region.value, v.partnership.value, v.model_dump_json()) for v in venues]
        with self._conn() as c:
            c.executemany(
                "INSERT INTO private_venues (id, region, partnership, data) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET region=excluded.region, partnership=excluded.partnership, "
                "data=excluded.data",
                rows,
            )

    def venues(self, region: RegionId) -> list[PrivateVenue]:
        with self._conn() as c:
            rows = c.execute("SELECT data FROM private_venues WHERE region = ?", (region.value,)).fetchall()
        return [PrivateVenue.model_validate_json(r[0]) for r in rows]

    def remove_places(self, ids: list[str]) -> None:
        """Used once to move private venues out of an older database's places table."""
        with self._conn() as c:
            c.executemany("DELETE FROM places WHERE id = ?", [(i,) for i in ids])

    # ---------------- itineraries ----------------
    def save_itinerary(self, it: Itinerary) -> None:
        now = _now()
        with self._conn() as c:
            c.execute(
                "INSERT INTO itineraries (id, version, data, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (str(it.id), it.version, it.model_dump_json(), now, now),
            )

    def get_itinerary(self, itinerary_id: UUID) -> Itinerary | None:
        with self._conn() as c:
            row = c.execute("SELECT data FROM itineraries WHERE id = ?", (str(itinerary_id),)).fetchone()
        return Itinerary.model_validate_json(row[0]) if row else None

    def replace_itinerary(self, it: Itinerary, expected_version: int) -> None:
        """Save only if nobody else saved in between (optimistic lock)."""
        with self._conn() as c:
            cur = c.execute(
                "UPDATE itineraries SET version = ?, data = ?, updated_at = ? WHERE id = ? AND version = ?",
                (it.version, it.model_dump_json(), _now(), str(it.id), expected_version),
            )
            if cur.rowcount != 1:
                raise StaleVersion(str(it.id))

    # ---------------- owner submissions ----------------
    def add_submission(self, sub: Submission, matched_place_id: str | None, score: float | None) -> int:
        with self._conn() as c:
            cur = c.execute(
                "INSERT INTO submissions (data, matched_place_id, match_score, created_at) VALUES (?, ?, ?, ?)",
                (sub.model_dump_json(), matched_place_id, score, _now()),
            )
            return int(cur.lastrowid or 0)
