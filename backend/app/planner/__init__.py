"""Build an itinerary from the intake. Deterministic: same input, same plan."""

from __future__ import annotations

from datetime import date, timedelta
from uuid import uuid4

from ..regions import RegionConfig
from ..routing import EstimateRouter, Router, RoutingUnavailable
from ..schema import DayPlan, Itinerary, LatLng, Providers, TripIntake
from .catalog import Catalog
from .days import DayBuilder
from .timeline import Visit, build_day
from .warnings import day_warnings


def _dates(intake: TripIntake) -> list[date]:
    return [intake.start_date + timedelta(days=i) for i in range(intake.trip_days)]


def plan_visits(intake: TripIntake, stay: LatLng, catalog: Catalog, region: RegionConfig) -> list[list[Visit]]:
    used: set[str] = set()
    return [DayBuilder(intake, region, catalog, stay, used).build() for _ in _dates(intake)]


def time_days(intake: TripIntake, stay: LatLng, visits: list[list[Visit]], catalog: Catalog,
              router: Router, region: RegionConfig) -> tuple[list[DayPlan], str]:
    """Apply real drive times. Falls back to estimates for the whole trip if OSRM fails."""
    for r in (router, EstimateRouter()):
        try:
            days = [build_day(d, i, v, stay, r, region)[0] for i, (d, v) in enumerate(zip(_dates(intake), visits))]
        except RoutingUnavailable:
            continue
        degraded = r.name == "estimate" and router.name != "estimate"
        return [day_warnings(d, intake, catalog, degraded) for d in days], r.name
    raise AssertionError("the estimate router never fails")


def region_for(intake: TripIntake, region: RegionConfig) -> RegionConfig:
    """The region's settings, with each day starting when the traveller asked."""
    return region.model_copy(update={"day_start": intake.start_time})


def build_itinerary(intake: TripIntake, stay: LatLng, catalog: Catalog, router: Router,
                    region: RegionConfig) -> Itinerary:
    region = region_for(intake, region)
    visits = plan_visits(intake, stay, catalog, region)
    days, routing = time_days(intake, stay, visits, catalog, router, region)
    return Itinerary(
        id=uuid4(), version=1, intake=intake, stay_coords=stay, days=days,
        generated_at=region.now(),
        providers=Providers(routing=routing, places="osm", llm=None),
    )
