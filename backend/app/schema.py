"""Data contracts for the trip planner (beta: Laguna, OSM-only, car-only).

Three contracts live here:
  1. TripIntake      - the 5 user inputs sent by the Nuxt intake form.
  2. Itinerary       - what the API returns and the frontend renders.
  3. LLMDayPicks     - the only shape the LLM is allowed to produce.

Rules enforced by the models themselves (not by callers):
  - Unknown keys are rejected everywhere (extra="forbid"); models are immutable.
  - A day's legs form one closed loop: stay -> stop 1 -> ... -> stop n -> stay.
  - No place appears on two days of the same itinerary.
  - Day dates match the intake's date range exactly.
  - The LLM never returns coordinates, times or legs; only place IDs + short text.
"""

from __future__ import annotations

from datetime import date, datetime, time
from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

MAX_TRIP_DAYS = 14
MAX_STOPS_PER_DAY = 8
MAX_PLACES_PER_DAY = 6  # places a traveller can ask for; meals come on top
EARLIEST_START = time(5, 0)
LATEST_START = time(12, 0)
SWAP_RADIUS_MIN_M = 3000
SWAP_RADIUS_MAX_M = 5000
STAY_ID = "stay"

# "osm:node/123", "osm:way/456", "osm:relation/789", or "curated:<slug>"
PlaceId = Annotated[
    str,
    Field(pattern=r"^(osm:(node|way|relation)/\d+|curated:[a-z0-9-]{1,64})$"),
]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


# --------------------------------------------------------------------------
# Enums
# --------------------------------------------------------------------------
class RegionId(StrEnum):
    """Beta launches with Calamba; other Laguna cities are added here."""

    CALAMBA = "calamba"


class GroupSize(StrEnum):
    SOLO = "solo"
    DUO = "duo"
    GROUP = "group"


class BudgetTier(StrEnum):
    BUDGET = "budget"
    MID = "mid"
    PREMIUM = "premium"


class AccessNeed(StrEnum):
    WHEELCHAIR = "wheelchair"
    MINIMAL_WALKING = "minimal_walking"
    SENSORY_FRIENDLY = "sensory_friendly"


class Interest(StrEnum):
    TRADITIONAL_FOOD = "traditional_food"
    SEAFOOD = "seafood"
    CAFES = "cafes"
    MALLS = "malls"
    WATERFALLS = "waterfalls"
    FARMS = "farms"
    PARKS = "parks"
    HOT_SPRINGS = "hot_springs"  # Alli 2026-11-18: hot springs & resorts interest


class AccessStatus(StrEnum):
    YES = "yes"
    LIMITED = "limited"
    NO = "no"
    UNKNOWN = "unknown"


class WarningCode(StrEnum):
    STOP_CLOSED_RESCHEDULED = "stop_closed_rescheduled"
    HOURS_UNVERIFIED = "hours_unverified"
    ACCESS_UNVERIFIED = "access_unverified"
    PEAK_TRAFFIC_LEG = "peak_traffic_leg"
    UNREACHABLE_BY_ROAD = "unreachable_by_road"
    LIGHT_DAY = "light_day"
    DAY_TRIMMED = "day_trimmed"
    NO_NEARBY_ALTERNATIVE = "no_nearby_alternative"
    STAY_AMBIGUOUS = "stay_ambiguous"
    DEGRADED_DATA = "degraded_data"


# --------------------------------------------------------------------------
# Geometry
# --------------------------------------------------------------------------
class LatLng(Strict):
    lat: Annotated[float, Field(ge=-90, le=90)]
    lng: Annotated[float, Field(ge=-180, le=180)]


class BBox(Strict):
    south: Annotated[float, Field(ge=-90, le=90)]
    west: Annotated[float, Field(ge=-180, le=180)]
    north: Annotated[float, Field(ge=-90, le=90)]
    east: Annotated[float, Field(ge=-180, le=180)]

    @model_validator(mode="after")
    def _ordered(self) -> BBox:
        if self.south >= self.north or self.west >= self.east:
            raise ValueError("bbox must have south < north and west < east")
        return self

    def contains(self, p: LatLng) -> bool:
        return self.south <= p.lat <= self.north and self.west <= p.lng <= self.east


# --------------------------------------------------------------------------
# 1. Intake (the 5 inputs)
# --------------------------------------------------------------------------
class StayLocation(Strict):
    label: Annotated[str, Field(min_length=1, max_length=200)]
    coords: LatLng | None = None  # server geocodes (Nominatim) when None


class StaySuggestion(Strict):
    """A hotel, guest house or resort offered while the traveller types where they stay."""
    name: str
    kind: str
    coords: LatLng


class TripIntake(Strict):
    region: RegionId = RegionId.CALAMBA
    # input 1: stay location & dates
    stay: StayLocation
    start_date: date
    end_date: date  # the same as start_date for a one-day trip
    start_time: time = time(8, 0)  # when the traveller wants to leave their stay each day
    # input 2: group size
    group: GroupSize
    group_count: Annotated[int, Field(ge=3, le=30)] | None = None
    # input 3: budget. The traveller types an amount; the website turns it into a tier.
    budget: BudgetTier
    budget_php: Annotated[int, Field(ge=0, le=10_000_000)] | None = None  # kept for budget estimates later
    # How many places (not counting meals) to visit each day. None = as many as fit.
    places_per_day: Annotated[int, Field(ge=1, le=MAX_PLACES_PER_DAY)] | None = None
    include_meals: bool = True  # False = they bring their own food: no lunch or dinner stops
    # input 4: accessibility / assistive needs
    access_needs: frozenset[AccessNeed] = frozenset()
    # input 5: optional interests, detected from what the traveller typed
    interests: frozenset[Interest] = frozenset()
    interests_text: Annotated[str, Field(max_length=300)] | None = None  # the words they typed
    # Beta decision (2026-11-18): unknown/limited access is shown with a warning.
    allow_unverified_access: bool = True

    @property
    def trip_days(self) -> int:
        return (self.end_date - self.start_date).days + 1

    @model_validator(mode="after")
    def _check(self) -> TripIntake:
        if not 1 <= self.trip_days <= MAX_TRIP_DAYS:
            raise ValueError(f"trip must be 1-{MAX_TRIP_DAYS} days")
        if not EARLIEST_START <= self.start_time <= LATEST_START:
            raise ValueError(f"start_time must be between {EARLIEST_START:%H:%M} and {LATEST_START:%H:%M}")
        if (self.group is GroupSize.GROUP) != (self.group_count is not None):
            raise ValueError("group_count is required for 'group' and only for 'group'")
        return self


# --------------------------------------------------------------------------
# Places
# --------------------------------------------------------------------------
class Accessibility(Strict):
    wheelchair: AccessStatus = AccessStatus.UNKNOWN
    sensory_friendly: AccessStatus = AccessStatus.UNKNOWN
    walk_m_estimate: Annotated[int, Field(ge=0)] | None = None
    rough_terrain: bool = False  # sac_scale / path-only access / steps
    sources: tuple[Literal["osm", "curated"], ...] = ()


class Place(Strict):
    id: PlaceId
    name: Annotated[str, Field(min_length=1, max_length=200)]
    coords: LatLng
    category: Interest | Literal["landmark", "other"]
    outdoor: bool
    price_tier: BudgetTier | None = None  # OSM rarely has prices; curated overrides
    accessibility: Accessibility = Accessibility()
    opening_hours: str | None = None  # raw OSM opening_hours syntax
    hours_verified: bool = False


# --------------------------------------------------------------------------
# 2. Itinerary
# --------------------------------------------------------------------------
class ItineraryWarning(Strict):
    code: WarningCode
    message: Annotated[str, Field(max_length=300)]
    place_id: PlaceId | None = None


class Leg(Strict):
    from_id: str  # STAY_ID or a PlaceId
    to_id: str
    distance_m: Annotated[int, Field(ge=0)]
    duration_s: Annotated[int, Field(ge=0)]  # after traffic factor
    traffic_factor: Annotated[float, Field(ge=1.0, le=4.0)] = 1.0
    geometry: str  # encoded polyline, precision 6 (OSRM geometries=polyline6)


class Stop(Strict):
    order: Annotated[int, Field(ge=0)]
    place: Place
    arrive: time
    depart: time
    dwell_min: Annotated[int, Field(ge=15, le=240)]
    reason: Annotated[str, Field(max_length=280)]

    @model_validator(mode="after")
    def _times(self) -> Stop:
        if self.depart <= self.arrive:
            raise ValueError("depart must be after arrive")
        return self


class DayPlan(Strict):
    date: date
    cluster_id: Annotated[int, Field(ge=0)]
    centroid: LatLng
    radius_m: Annotated[int, Field(ge=0)]
    stops: Annotated[list[Stop], Field(max_length=MAX_STOPS_PER_DAY)]
    legs: list[Leg]
    total_travel_s: Annotated[int, Field(ge=0)]
    warnings: list[ItineraryWarning] = []

    @model_validator(mode="after")
    def _closed_loop(self) -> DayPlan:
        if [s.order for s in self.stops] != list(range(len(self.stops))):
            raise ValueError("stop.order must be 0..n-1 in list order")
        if not self.stops:
            if self.legs:
                raise ValueError("a rest day has no legs")
            return self
        chain = [STAY_ID, *(s.place.id for s in self.stops), STAY_ID]
        expected = list(zip(chain, chain[1:]))
        actual = [(leg.from_id, leg.to_id) for leg in self.legs]
        if actual != expected:
            raise ValueError("legs must form one loop: stay -> stops in order -> stay")
        if self.total_travel_s != sum(leg.duration_s for leg in self.legs):
            raise ValueError("total_travel_s must equal the sum of leg durations")
        for a, b in zip(self.stops, self.stops[1:]):
            if b.arrive < a.depart:
                raise ValueError("stops overlap in time")
        return self


class Providers(Strict):
    routing: Literal["osrm", "estimate"] = "osrm"  # estimate = OSRM was unreachable
    places: Literal["osm"] = "osm"
    llm: str | None = None  # None = deterministic fallback, no LLM used


class Itinerary(Strict):
    id: UUID
    version: Annotated[int, Field(ge=1)]  # bumps on every applied swap
    intake: TripIntake
    stay_coords: LatLng
    days: list[DayPlan]
    generated_at: datetime
    providers: Providers = Providers()

    @model_validator(mode="after")
    def _consistent(self) -> Itinerary:
        want = [
            date.fromordinal(self.intake.start_date.toordinal() + i)
            for i in range(self.intake.trip_days)
        ]
        if [d.date for d in self.days] != want:
            raise ValueError("days must cover start_date..end_date, one per date, in order")
        seen: set[str] = set()
        for day in self.days:
            for stop in day.stops:
                if stop.place.id in seen:
                    raise ValueError(f"place {stop.place.id} appears on more than one day")
                seen.add(stop.place.id)
        return self


# --------------------------------------------------------------------------
# Swap
# --------------------------------------------------------------------------
class SwapRequest(Strict):
    version: Annotated[int, Field(ge=1)]  # optimistic lock against stale clients
    day_index: Annotated[int, Field(ge=0)]
    stop_order: Annotated[int, Field(ge=0)]
    radius_m: Annotated[int, Field(ge=SWAP_RADIUS_MIN_M, le=SWAP_RADIUS_MAX_M)] = SWAP_RADIUS_MIN_M
    exclude_ids: Annotated[list[PlaceId], Field(max_length=50)] = []


class SwapCandidate(Strict):
    place: Place
    delta_travel_s: int  # insertion delta; negative = route gets shorter
    distance_from_old_m: Annotated[int, Field(ge=0, le=20_000)]
    warnings: list[ItineraryWarning] = []


class StopChoices(Strict):
    """Other places the traveller can pick for one stop of a day."""
    stop_order: Annotated[int, Field(ge=0)]
    options: list[SwapCandidate]


class StopRemove(Strict):
    version: Annotated[int, Field(ge=1)]
    day_index: Annotated[int, Field(ge=0)]
    stop_order: Annotated[int, Field(ge=0)]


class StopAdd(Strict):
    version: Annotated[int, Field(ge=1)]
    day_index: Annotated[int, Field(ge=0)]
    new_place_id: PlaceId
    part: Literal["morning", "afternoon", "evening"]
    meal: Literal["lunch", "dinner"] | None = None  # puts a restaurant back (undo); the place must be one


class SwapApply(Strict):
    version: Annotated[int, Field(ge=1)]
    day_index: Annotated[int, Field(ge=0)]
    stop_order: Annotated[int, Field(ge=0)]
    new_place_id: PlaceId


# --------------------------------------------------------------------------
# 3. What the LLM may return (sent as the forced tool's input_schema)
# --------------------------------------------------------------------------
class LLMStopPick(Strict):
    place_id: PlaceId  # must be in the candidate set given for that day
    reason: Annotated[str, Field(min_length=1, max_length=280)]


class LLMDayPicks(Strict):
    day_index: Annotated[int, Field(ge=0)]
    picks: Annotated[list[LLMStopPick], Field(min_length=1, max_length=MAX_STOPS_PER_DAY)]

    def unknown_ids(self, candidate_ids: set[str]) -> list[str]:
        """IDs the model invented or took from another day. Non-empty = reject."""
        return [p.place_id for p in self.picks if p.place_id not in candidate_ids]


class LLMPlan(Strict):
    days: Annotated[list[LLMDayPicks], Field(min_length=1, max_length=MAX_TRIP_DAYS)]
