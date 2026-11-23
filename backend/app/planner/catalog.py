"""The places the planner may use, grouped by the role they play in a day."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from ..places.models import PlaceRecord, PlaceStatus
from ..schema import Accessibility, AccessStatus, Interest, Place

USABLE = frozenset({PlaceStatus.FEATURED, PlaceStatus.LISTED})

MEAL_KINDS = frozenset({"restaurant", "fast_food"})
CAFE_KINDS = frozenset({"cafe", "bakery"})
# Kinds that are never a sightseeing stop on their own.
NOT_SIGHTS = frozenset({"hotel", "guest_house", "place_of_worship", "sports_centre", "cinema", "golf_course"})


class Role(StrEnum):
    SIGHT = "sight"
    MEAL = "meal"
    CAFE = "cafe"


def role_of(p: PlaceRecord) -> Role | None:
    if p.category in (Interest.TRADITIONAL_FOOD, Interest.SEAFOOD) or p.kind in MEAL_KINDS:
        return Role.MEAL
    if p.category == Interest.CAFES or p.kind in CAFE_KINDS:
        return Role.CAFE
    curated = p.status_reason == "curated:sheet"
    if p.kind in NOT_SIGHTS and not curated:
        return None
    if p.category == "other" and not curated:
        return None
    return Role.SIGHT


def is_curated(p: PlaceRecord) -> bool:
    return p.status_reason == "curated:sheet"


DWELL_MIN = {"landmark": 45, Interest.PARKS: 75, Interest.HOT_SPRINGS: 180, Interest.MALLS: 90, "other": 60}
KIND_DWELL_MIN = {"museum": 75, "curated": 60}


def dwell_for(p: PlaceRecord, role: Role) -> int:
    if role is Role.MEAL:
        return 60
    if role is Role.CAFE:
        return 45
    if p.name.lower().startswith("rizal shrine"):
        return 75  # museum visit; curated rows don't carry the OSM kind
    return KIND_DWELL_MIN.get(p.kind, DWELL_MIN.get(p.category, 60))


def to_place(p: PlaceRecord) -> Place:
    """The public shape sent to the website."""
    return Place(
        id=p.id, name=p.name, coords=p.coords, category=p.category, outdoor=p.outdoor,
        accessibility=Accessibility(
            wheelchair=p.wheelchair,
            sources=("curated",) if p.overrides.get("wheelchair") else ("osm",),
        ),
        opening_hours=p.opening_hours,
        hours_verified=p.overrides.get("opening_hours") == "owner",
    )


@dataclass
class Catalog:
    """Every usable place in one region, loaded once at startup."""

    by_id: dict[str, PlaceRecord]
    details: dict[str, str] = field(default_factory=dict)

    @classmethod
    def build(cls, places: list[PlaceRecord], details: dict[str, str]) -> Catalog:
        return cls({p.id: p for p in places if p.status in USABLE and not p.possibly_closed}, details)

    def with_role(self, role: Role) -> list[PlaceRecord]:
        return [p for p in self.by_id.values() if role_of(p) is role]


def access_ok(p: PlaceRecord, wheelchair: bool, allow_unverified: bool) -> bool:
    if not wheelchair:
        return True
    if p.wheelchair is AccessStatus.NO:
        return False
    return allow_unverified or p.wheelchair in (AccessStatus.YES, AccessStatus.LIMITED)
