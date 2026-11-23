"""Warnings that depend on a whole timed day."""

from __future__ import annotations

from ..schema import (
    AccessNeed,
    AccessStatus,
    DayPlan,
    ItineraryWarning,
    TripIntake,
    WarningCode,
)
from .catalog import Catalog, Role, role_of

LIGHT_DAY_SIGHTS = 2
DEGRADED = ItineraryWarning(
    code=WarningCode.DEGRADED_DATA,
    message="Drive times are estimates today because our route service didn't respond.",
)


def day_warnings(day: DayPlan, intake: TripIntake, catalog: Catalog, degraded: bool) -> DayPlan:
    """Warnings that depend on the whole day, added after timing."""
    extra: list[ItineraryWarning] = []
    if AccessNeed.WHEELCHAIR in intake.access_needs:
        for s in day.stops:
            wc = s.place.accessibility.wheelchair
            if wc is AccessStatus.UNKNOWN:
                msg = f"{s.place.name} has no step-free access info yet. Call ahead if you use a wheelchair."
            elif wc is AccessStatus.LIMITED:
                msg = f"{s.place.name} is only partly step-free. Call ahead to check the parts you need."
            else:
                continue
            extra.append(ItineraryWarning(code=WarningCode.ACCESS_UNVERIFIED, message=msg, place_id=s.place.id))
    sights = sum(1 for s in day.stops if role_of(catalog.by_id[s.place.id]) is Role.SIGHT)
    if sights < LIGHT_DAY_SIGHTS:
        extra.append(ItineraryWarning(
            code=WarningCode.LIGHT_DAY,
            message="A light day: we ran out of nearby places that fit your choices." if day.stops
            else "A free day: every place that fits your choices is already on another day.",
        ))
    if degraded:
        extra.append(DEGRADED)
    return day.model_copy(update={"warnings": [*day.warnings, *extra]})
