"""Swap one stop for a nearby place that plays the same role (sight for sight, meal for meal)."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, time, timedelta

from ..places.matching import distance_m
from ..places.models import PlaceRecord
from ..regions import RegionConfig
from ..routing import EstimateRouter, Router, RoutingUnavailable
from ..schema import (
    MAX_STOPS_PER_DAY,
    SWAP_RADIUS_MAX_M,
    AccessNeed,
    DayPlan,
    Itinerary,
    ItineraryWarning,
    LatLng,
    StopAdd,
    StopChoices,
    StopRemove,
    SwapApply,
    SwapCandidate,
    SwapRequest,
    WarningCode,
)
from .catalog import Catalog, Role, access_ok, dwell_for, role_of, to_place
from .days import LIMIT_PER_DAY
from .reasons import reason_for
from .scoring import ALWAYS, MIX, score, sight_allowed
from .timeline import Visit, build_day
from .warnings import day_warnings

MAX_OPTIONS = 5
CHOICES_PER_STOP = 3  # suggestions shown under each stop on the trip page
_est = EstimateRouter()


class SwapError(ValueError):
    """Bad day or stop index, or a place that can't be swapped in. Message is user-facing."""


def _neighbours(it: Itinerary, day: DayPlan, order: int) -> tuple[LatLng, LatLng]:
    prev = day.stops[order - 1].place.coords if order > 0 else it.stay_coords
    nxt = day.stops[order + 1].place.coords if order + 1 < len(day.stops) else it.stay_coords
    return prev, nxt


def _locate(it: Itinerary, day_index: int, stop_order: int) -> DayPlan:
    if day_index >= len(it.days) or stop_order >= len(it.days[day_index].stops):
        raise SwapError("That stop is no longer in this plan. Reload the page and try again.")
    return it.days[day_index]


def _eligible(it: Itinerary, catalog: Catalog, role: Role, exclude: set[str]) -> list[PlaceRecord]:
    intake = it.intake
    wheelchair = AccessNeed.WHEELCHAIR in intake.access_needs
    used = {s.place.id for d in it.days for s in d.stops} | exclude
    return [
        p for p in catalog.by_id.values()
        if p.id not in used and role_of(p) is role
        and access_ok(p, wheelchair, intake.allow_unverified_access)
        and (role is not Role.SIGHT or sight_allowed(p, intake))
    ]


def _candidate_warnings(p: PlaceRecord) -> list[ItineraryWarning]:
    # Wheelchair access is already shown on the candidate's access badge.
    out = []
    if not p.opening_hours:
        out.append(ItineraryWarning(code=WarningCode.HOURS_UNVERIFIED,
                                    message="Opening hours not confirmed.", place_id=p.id))
    return out


def swap_options(it: Itinerary, req: SwapRequest, catalog: Catalog) -> list[SwapCandidate]:
    day = _locate(it, req.day_index, req.stop_order)
    old = day.stops[req.stop_order].place
    old_rec = catalog.by_id.get(old.id)
    if old_rec is None:
        return []
    role = role_of(old_rec)
    assert role is not None
    prev, nxt = _neighbours(it, day, req.stop_order)
    base = _est.drive(prev, old.coords).duration_s + _est.drive(old.coords, nxt).duration_s
    pool = _eligible(it, catalog, role, set(req.exclude_ids))
    # Keep the day's own limits (one hot spring, one mall) when swapping sights.
    others = [catalog.by_id[s.place.id].category for s in day.stops
              if s.order != req.stop_order and s.place.id in catalog.by_id]
    pool = [p for p in pool if others.count(p.category) < LIMIT_PER_DAY.get(p.category, 99)]

    for radius in (req.radius_m, SWAP_RADIUS_MAX_M):
        near = [(p, distance_m(old.coords, p.coords)) for p in pool]
        near = [(p, d) for p, d in near if d <= radius]
        if near:
            break
    # Like for like first: a landmark is swapped for another landmark when one is near.
    ranked = sorted(near, key=lambda pd: (pd[0].category != old_rec.category,
                                          -score(pd[0], role, it.intake), pd[1]))[:MAX_OPTIONS]
    out = []
    for p, d in ranked:
        delta = _est.drive(prev, p.coords).duration_s + _est.drive(p.coords, nxt).duration_s - base
        out.append(SwapCandidate(place=to_place(p), delta_travel_s=delta, distance_from_old_m=round(d),
                                 warnings=_candidate_warnings(p)))
    return out


def day_choices(it: Itinerary, day_index: int, catalog: Catalog) -> list[StopChoices]:
    """Suggestions for every stop of a day. The trip page shows them one at a time per part of the day."""
    if day_index >= len(it.days):
        raise SwapError("That day is no longer in this plan. Reload the page and try again.")
    return [
        StopChoices(stop_order=stop.order, options=swap_options(
            it, SwapRequest(version=it.version, day_index=day_index, stop_order=stop.order), catalog,
        )[:CHOICES_PER_STOP])
        for stop in it.days[day_index].stops
    ]


def apply_swap(it: Itinerary, req: SwapApply, catalog: Catalog, router: Router,
               region: RegionConfig) -> Itinerary:
    """Returns the updated itinerary with version + 1. The caller saves it with a version check."""
    day = _locate(it, req.day_index, req.stop_order)
    old_rec = catalog.by_id.get(day.stops[req.stop_order].place.id)
    new_rec = catalog.by_id.get(req.new_place_id)
    if old_rec is None or new_rec is None:
        raise SwapError("That place isn't available any more. Pick another option.")
    role = role_of(old_rec)
    if role is None or new_rec not in _eligible(it, catalog, role, set()):
        raise SwapError("That place can't replace this stop. Pick another option.")

    visits = _visits(day, catalog, region)
    old_slot = visits[req.stop_order]
    visits[req.stop_order] = Visit(new_rec, dwell_for(new_rec, role),
                                   reason_for(new_rec, role, catalog.details,
                                              meal=_meal_label(old_slot), prev_name=None),
                                   not_before=old_slot.not_before)

    return _rebuild(it, req.day_index, visits, catalog, router, region)[0]


def _visits(day: DayPlan, catalog: Catalog, region: RegionConfig) -> list[Visit]:
    """The day's stops as visits again, keeping meal hours and any planned wait."""
    visits = []
    for s in day.stops:
        rec = catalog.by_id.get(s.place.id)
        if rec is None:
            raise SwapError("Part of this day is no longer available. Make a new plan.")
        if role_of(rec) is Role.MEAL:
            not_before = _meal_slot(s.arrive)
        else:  # keep a planned wait, like the afternoon start when they bring their own food
            not_before = s.arrive if _waited(day, s.order, region) else None
        visits.append(Visit(rec, s.dwell_min, s.reason, not_before=not_before))
    return visits


def _refresh_meal_reasons(visits: list[Visit], catalog: Catalog) -> list[Visit]:
    """A meal reason says which stop it is near. After an edit that stop may be gone, so say it again."""
    out = []
    for i, v in enumerate(visits):
        if role_of(v.place) is Role.MEAL and v.not_before is not None:
            prev = visits[i - 1].place.name if i > 0 else None
            v = replace(v, reason=reason_for(v.place, Role.MEAL, catalog.details, meal=_meal_label(v), prev_name=prev))
        out.append(v)
    return out


def _rebuild(it: Itinerary, day_index: int, visits: list[Visit], catalog: Catalog, router: Router,
             region: RegionConfig) -> tuple[Itinerary, list[Visit]]:
    """Builds the day again from these visits and returns the plan with version + 1."""
    day = it.days[day_index]
    visits = _refresh_meal_reasons(visits, catalog)
    degraded = False
    try:
        new_day, trimmed = build_day(day.date, day.cluster_id, visits, it.stay_coords, router, region)
    except RoutingUnavailable:
        new_day, trimmed = build_day(day.date, day.cluster_id, visits, it.stay_coords, _est, region)
        degraded = True
    new_day = day_warnings(new_day, it.intake, catalog, degraded)
    days = list(it.days)
    days[day_index] = new_day
    return it.model_copy(update={"days": days, "version": it.version + 1}), trimmed


def _waited(day: DayPlan, order: int, region: RegionConfig) -> bool:
    """True when the plan holds this stop until a set time instead of arriving straight away."""
    if order == 0:
        return False
    prev = day.stops[order - 1].depart
    reach = datetime.combine(day.date, prev) + timedelta(seconds=day.legs[order].duration_s)
    return datetime.combine(day.date, day.stops[order].arrive) - reach > timedelta(minutes=2)


def _meal_slot(arrive: time | None) -> time | None:
    if arrive is None:
        return None
    return time(11, 30) if arrive < time(15, 0) else time(18, 0)


def _meal_label(v: Visit) -> str:
    if v.not_before is None:
        return ""
    return "lunch" if v.not_before.hour < 15 else "dinner"


# ---- Adding and removing places -------------------------------------------------------------

RECOMMENDATIONS = 12  # places offered below the plan
RECOMMEND_RADIUS_M = 15_000  # all of Calamba is within this of a day's route
EVENING_AT = time(17, 0)
AFTERNOON_AT = time(13, 0)
_PARTS = ("morning", "afternoon", "evening")


def _is_meal(v: Visit) -> bool:
    return role_of(v.place) is Role.MEAL


def _insert_at(stops_arrive: list[time], visits: list[Visit], part: str) -> int:
    """Where in the day a place for this part of the day goes."""
    n = len(visits)
    if part == "morning":  # before lunch, or before the first afternoon stop
        return next((i for i, v in enumerate(visits)
                     if (_is_meal(v) and stops_arrive[i] < time(15, 0)) or stops_arrive[i] >= time(12, 0)), n)
    if part == "afternoon":  # after lunch, before any evening stop
        return next((i for i, a in enumerate(stops_arrive) if a >= EVENING_AT), n)
    # evening: before dinner when there is one, so dinner stays the last stop of the day
    return next((i for i, v in enumerate(visits) if _is_meal(v) and stops_arrive[i] >= EVENING_AT), n)


def _addable(it: Itinerary, catalog: Catalog) -> list[PlaceRecord]:
    """Sights the traveller can add. Wider than the plan itself: anyone browsing for more can
    also be offered places outside the interests they ticked."""
    intake = it.intake
    wheelchair = AccessNeed.WHEELCHAIR in intake.access_needs
    used = {s.place.id for d in it.days for s in d.stops}
    return [
        p for p in catalog.by_id.values()
        if p.id not in used and role_of(p) is Role.SIGHT
        and access_ok(p, wheelchair, intake.allow_unverified_access)
        and (p.category in MIX or p.category in ALWAYS or p.category in intake.interests)
    ]


def _insertion_delta(day: DayPlan, stay: LatLng, p: PlaceRecord) -> int:
    pts = [stay, *[s.place.coords for s in day.stops], stay]
    best = min(
        _est.drive(a, p.coords).duration_s + _est.drive(p.coords, b).duration_s - _est.drive(a, b).duration_s
        for a, b in zip(pts, pts[1:], strict=False)
    )
    return best


def day_recommendations(it: Itinerary, day_index: int, catalog: Catalog,
                        limit: int = RECOMMENDATIONS) -> list[SwapCandidate]:
    """Places the traveller can add to a day, nearest to the day's route first."""
    if day_index >= len(it.days):
        raise SwapError("That day is no longer in this plan. Reload the page and try again.")
    day = it.days[day_index]
    pool = _addable(it, catalog)
    kept = [catalog.by_id[s.place.id].category for s in day.stops if s.place.id in catalog.by_id]
    pool = [p for p in pool if kept.count(p.category) < LIMIT_PER_DAY.get(p.category, 99)]
    centre = day.centroid
    near = [(p, distance_m(centre, p.coords)) for p in pool]
    near = sorted((pd for pd in near if pd[1] <= RECOMMEND_RADIUS_M),
                  key=lambda pd: (-score(pd[0], Role.SIGHT, it.intake), pd[1]))[:limit]
    return [
        SwapCandidate(place=to_place(p), delta_travel_s=max(0, _insertion_delta(day, it.stay_coords, p)),
                      distance_from_old_m=round(d), warnings=_candidate_warnings(p))
        for p, d in near
    ]


def apply_add(it: Itinerary, req: StopAdd, catalog: Catalog, router: Router,
              region: RegionConfig) -> Itinerary:
    """Adds a place to the morning, afternoon or evening of a day. Version + 1."""
    if req.day_index >= len(it.days):
        raise SwapError("That day is no longer in this plan. Reload the page and try again.")
    day = it.days[req.day_index]
    if len(day.stops) >= MAX_STOPS_PER_DAY:
        raise SwapError("This day is full. Remove a place first, then add this one.")
    new_rec = catalog.by_id.get(req.new_place_id)
    pool = _eligible(it, catalog, Role.MEAL, set()) if req.meal else _addable(it, catalog)
    if new_rec is None or new_rec not in pool:
        raise SwapError("That place can't be added. Pick another one.")

    visits = _visits(day, catalog, region)
    if req.meal:  # putting a lunch or dinner back where it was
        slot = time(11, 30) if req.meal == "lunch" else time(18, 0)
        arrives = [s.arrive for s in day.stops]
        at = len(visits) if req.meal == "dinner" else next(
            (i for i, a in enumerate(arrives) if a >= time(12, 0)), len(visits))
        visits.insert(at, Visit(new_rec, dwell_for(new_rec, Role.MEAL), "", not_before=slot))
        updated, trimmed = _rebuild(it, req.day_index, visits, catalog, router, region)
        if any(v.place.id == new_rec.id for v in trimmed):
            raise SwapError("That meal doesn't fit in this day without running late.")
        return updated
    at = _insert_at([s.arrive for s in day.stops], visits, req.part)
    not_before = {"morning": None, "afternoon": AFTERNOON_AT, "evening": EVENING_AT}[req.part]
    new = Visit(new_rec, dwell_for(new_rec, Role.SIGHT),
                reason_for(new_rec, Role.SIGHT, catalog.details, meal="", prev_name=None),
                not_before=not_before)
    visits.insert(at, new)
    updated, trimmed = _rebuild(it, req.day_index, visits, catalog, router, region)
    if any(v.place.id == new_rec.id for v in trimmed):
        raise SwapError("That place doesn't fit in this day without running late. Try another time of day.")
    return updated


def apply_remove(it: Itinerary, req: StopRemove, catalog: Catalog, router: Router,
                 region: RegionConfig) -> Itinerary:
    """Takes a place out of a day. Version + 1."""
    day = _locate(it, req.day_index, req.stop_order)
    visits = _visits(day, catalog, region)
    del visits[req.stop_order]
    updated, _ = _rebuild(it, req.day_index, visits, catalog, router, region)
    return updated
