"""Records for the places data layer. Mirrors sql/001_places.sql."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field

from ..schema import AccessStatus, Interest, LatLng, RegionId, Strict

OsmRef = Annotated[str, Field(pattern=r"^(node|way|relation)/\d+$")]
Category = Interest | Literal["landmark", "other"]

# Fields an OSM refresh may write. Anything a person sets in `overrides` wins.
OSM_OWNED_FIELDS = ("name", "kind", "category", "coords", "outdoor", "wheelchair",
                    "opening_hours", "website", "is_chain")


class PlaceStatus(StrEnum):
    FEATURED = "featured"  # hand-picked; the AI builds days around these
    LISTED = "listed"      # searchable, used as meal/rest stops and swaps
    HIDDEN = "hidden"      # never shown (private pools, unnamed, duplicates)
    PENDING = "pending"    # no rule matched; waits for a person


class OsmRecord(Strict):
    """One OSM feature after normalising its tags. Becomes an osm_places row."""

    osm_ref: OsmRef
    region: RegionId
    name: Annotated[str, Field(min_length=1, max_length=200)]
    osm_key: str
    osm_value: str
    coords: LatLng
    tags: dict[str, str]


class PlaceRecord(Strict):
    """A row of `places`, the table the planner reads."""

    id: str
    osm_ref: OsmRef | None
    region: RegionId
    name: str
    category: Category
    kind: str
    coords: LatLng
    outdoor: bool = False
    is_chain: bool = False
    status: PlaceStatus = PlaceStatus.PENDING
    status_reason: str | None = None
    wheelchair: AccessStatus = AccessStatus.UNKNOWN
    opening_hours: str | None = None
    website: str | None = None
    overrides: dict[str, Literal["alli", "owner", "curated"]] = {}
    possibly_closed: bool = False


class Submission(Strict):
    """A business owner's form entry, before review."""

    region: RegionId
    business_name: Annotated[str, Field(min_length=2, max_length=200)]
    category: Category
    coords: LatLng
    opening_hours: str | None = None
    wheelchair: AccessStatus = AccessStatus.UNKNOWN
    website: str | None = None
    contact_email: Annotated[str, Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")]


class PartnershipStatus(StrEnum):
    NONE = "none"            # not contacted
    CONTACTED = "contacted"  # talking to the owner
    PARTNER = "partner"      # agreement in place; may be offered with booking later


class WalkIn(StrEnum):
    YES = "yes"          # takes walk-in guests: stored as a place, can be planned
    NO = "no"            # rented whole or booking only
    UNKNOWN = "unknown"  # no evidence yet; a person decides


class PrivateVenue(Strict):
    """A resort or pool that does not (or may not) take walk-ins. Kept apart from `places`:
    never used in plans until a partnership exists or a person marks it walk-in."""

    id: str
    osm_ref: OsmRef | None
    region: RegionId
    name: str
    kind: str
    coords: LatLng
    wheelchair: AccessStatus = AccessStatus.UNKNOWN
    opening_hours: str | None = None
    website: str | None = None
    details: str | None = None
    walk_in: WalkIn = WalkIn.UNKNOWN
    walk_in_reason: str | None = None
    partnership: PartnershipStatus = PartnershipStatus.NONE
