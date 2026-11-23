"""Turn an ordered list of visits into timed stops and legs (one closed loop)."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime, time, timedelta

from ..places.matching import distance_m
from ..places.models import PlaceRecord
from ..regions import RegionConfig, traffic_factor
from ..routing import Drive, Router
from ..schema import STAY_ID, DayPlan, ItineraryWarning, LatLng, Leg, Stop, WarningCode
from .catalog import to_place

LATEST_RETURN = time(22, 0)  # trim the day rather than plan past this


@dataclass(frozen=True)
class Visit:
    place: PlaceRecord
    dwell_min: int
    reason: str
    not_before: time | None = None  # lunch and dinner wait for a sensible hour


def _ceil5(d: datetime) -> datetime:
    """Round up to the next 5 minutes, so the plan reads 8:15 and not 8:11."""
    if d.second or d.microsecond:
        d = d.replace(second=0, microsecond=0) + timedelta(minutes=1)
    return d + timedelta(minutes=(-d.minute) % 5)


def _t(d: datetime) -> time:
    return d.time().replace(microsecond=0)


def _peak_message(factors: list[float]) -> str:
    worst = f"{max(factors):g}x"
    if len(factors) == 1:
        return f"One drive falls in rush hour, so it is planned at {worst} normal time."
    return f"{len(factors)} drives fall in rush hour, so they are planned at up to {worst} normal time."


def build_day(day: date, cluster_id: int, visits: list[Visit], stay: LatLng,
              router: Router, region: RegionConfig) -> tuple[DayPlan, list[Visit]]:
    """Returns the day and the visits that were trimmed because the day ran too late."""
    trimmed: list[Visit] = []
    while True:
        plan = _try_day(day, cluster_id, visits, stay, router, region)
        if plan is not None or not visits:
            break
        # Drop the last non-meal visit (or the last visit) and try again.
        idx = max((i for i, v in enumerate(visits) if v.not_before is None), default=len(visits) - 1)
        trimmed.append(visits[idx])
        visits = visits[:idx] + visits[idx + 1:]
    if plan is None:  # nothing fits at all: a rest day
        plan = _try_day(day, cluster_id, [], stay, router, region)
        assert plan is not None
    if trimmed:
        plan = plan.model_copy(update={"warnings": [*plan.warnings, ItineraryWarning(
            code=WarningCode.DAY_TRIMMED,
            message=f"We left out {', '.join(v.place.name for v in trimmed)} so the day ends at a reasonable time.",
        )]})
    return plan, trimmed


def _try_day(day: date, cluster_id: int, visits: list[Visit], stay: LatLng,
             router: Router, region: RegionConfig) -> DayPlan | None:
    if not visits:
        return DayPlan(date=day, cluster_id=cluster_id, centroid=stay, radius_m=0,
                       stops=[], legs=[], total_travel_s=0)
    clock = datetime.combine(day, region.day_start)
    pos, pos_id = stay, STAY_ID
    stops: list[Stop] = []
    legs: list[Leg] = []
    warnings: list[ItineraryWarning] = []
    peak: list[float] = []  # traffic factors of legs that fall in rush hour

    def add_leg(to: LatLng, to_id: str) -> timedelta:
        drive: Drive = router.drive(pos, to)
        f = traffic_factor(region, _t(clock))
        legs.append(Leg(from_id=pos_id, to_id=to_id, distance_m=drive.distance_m,
                        duration_s=round(drive.duration_s * f), traffic_factor=f, geometry=drive.geometry))
        if f > 1:
            peak.append(f)
        return timedelta(seconds=legs[-1].duration_s)

    for i, v in enumerate(visits):
        clock = _ceil5(clock + add_leg(v.place.coords, v.place.id))
        if v.not_before and _t(clock) < v.not_before:
            clock = datetime.combine(day, v.not_before)
        arrive = clock
        clock += timedelta(minutes=v.dwell_min)
        if clock.date() != day:
            return None
        stops.append(Stop(order=i, place=to_place(v.place), arrive=_t(arrive), depart=_t(clock),
                          dwell_min=v.dwell_min, reason=v.reason))
        pos, pos_id = v.place.coords, v.place.id
    clock += add_leg(stay, STAY_ID)
    if clock.date() != day or _t(clock) > LATEST_RETURN:
        return None

    if peak:
        warnings.append(ItineraryWarning(code=WarningCode.PEAK_TRAFFIC_LEG, message=_peak_message(peak)))
    pts = [v.place.coords for v in visits]
    centroid = LatLng(lat=sum(p.lat for p in pts) / len(pts), lng=sum(p.lng for p in pts) / len(pts))
    radius = max(round(distance_m(centroid, p)) for p in pts)
    return DayPlan(date=day, cluster_id=cluster_id, centroid=centroid, radius_m=radius, stops=stops,
                   legs=legs, total_travel_s=sum(leg.duration_s for leg in legs), warnings=warnings)


def with_visit(visits: list[Visit], index: int, new: Visit) -> list[Visit]:
    out = list(visits)
    out[index] = replace(new, not_before=visits[index].not_before)
    return out
