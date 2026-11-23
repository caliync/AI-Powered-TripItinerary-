from datetime import date, time

import httpx
import pytest

from app.planner import build_itinerary
from app.planner.catalog import Role, role_of
from app.planner.swap import SwapError, apply_swap, swap_options
from app.regions import REGIONS
from app.routing import EstimateRouter, OsrmRouter
from app.schema import AccessStatus, LatLng, SwapApply, SwapRequest, TripIntake, WarningCode

from .conftest import HOTEL_MARCIANO

CALAMBA = REGIONS["calamba"]
STAY = LatLng(**HOTEL_MARCIANO)


def intake(days=2, **kw):
    base = dict(stay={"label": "Hotel Marciano", "coords": HOTEL_MARCIANO}, start_date=date(2026, 12, 5),
                end_date=date(2026, 12, 4 + days), group="duo", budget="mid")
    base.update(kw)
    return TripIntake.model_validate(base)


def plan(catalog, **kw):
    return build_itinerary(intake(**kw), STAY, catalog, EstimateRouter(), CALAMBA)


def test_plan_is_valid_and_has_meals(catalog):
    it = plan(catalog, days=3)  # the Itinerary model itself checks loops, dates and no repeats
    assert len(it.days) == 3
    for day in it.days:
        roles = [role_of(catalog.by_id[s.place.id]) for s in day.stops]
        assert roles.count(Role.MEAL) == 2, day.stops  # lunch and dinner
        lunch = next(s for s in day.stops if role_of(catalog.by_id[s.place.id]) is Role.MEAL)
        assert lunch.arrive >= time(11, 30)
        assert day.stops[-1].arrive >= time(18, 0)


def test_same_input_same_plan(catalog):
    a, b = plan(catalog), plan(catalog)
    assert [s.place.id for d in a.days for s in d.stops] == [s.place.id for d in b.days for s in d.stops]


def test_interests_limit_sight_categories(catalog):
    it = plan(catalog, interests={"malls"})
    for d in it.days:
        for s in d.stops:
            if role_of(catalog.by_id[s.place.id]) is Role.SIGHT:
                assert s.place.category in ("landmark", "parks", "other", "malls")


def test_wheelchair_never_gets_no_and_unknown_is_warned(catalog):
    it = plan(catalog, access_needs={"wheelchair"})
    stops = [s for d in it.days for s in d.stops]
    assert all(s.place.accessibility.wheelchair is not AccessStatus.NO for s in stops)
    warned = {w.place_id for d in it.days for w in d.warnings if w.code is WarningCode.ACCESS_UNVERIFIED}
    unknown = {s.place.id for s in stops if s.place.accessibility.wheelchair is not AccessStatus.YES}
    assert unknown == warned


def test_strict_wheelchair_uses_only_known_access(catalog):
    it = plan(catalog, access_needs={"wheelchair"}, allow_unverified_access=False)
    for d in it.days:
        for s in d.stops:
            assert s.place.accessibility.wheelchair in (AccessStatus.YES, AccessStatus.LIMITED)


def test_long_trip_runs_out_gracefully(catalog):
    it = plan(catalog, days=14, interests={"waterfalls"})
    assert any(w.code is WarningCode.LIGHT_DAY for d in it.days for w in d.warnings)


def test_osrm_down_falls_back_to_estimates(catalog):
    down = OsrmRouter("https://osrm.test", httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(503))))
    it = build_itinerary(intake(), STAY, catalog, down, CALAMBA)
    assert it.providers.routing == "estimate"
    assert all(any(w.code is WarningCode.DEGRADED_DATA for w in d.warnings) for d in it.days)


def test_swap_options_same_role_nearby_and_unused(catalog):
    it = plan(catalog)
    day = it.days[0]
    lunch = next(s for s in day.stops if role_of(catalog.by_id[s.place.id]) is Role.MEAL)
    opts = swap_options(it, SwapRequest(version=1, day_index=0, stop_order=lunch.order), catalog)
    used = {s.place.id for d in it.days for s in d.stops}
    assert opts
    for c in opts:
        assert role_of(catalog.by_id[c.place.id]) is Role.MEAL
        assert c.place.id not in used
        assert c.distance_from_old_m <= 5000


def test_swap_prefers_same_category_and_keeps_day_limits(catalog):
    it = plan(catalog, interests={"malls"})
    for d_i, day in enumerate(it.days):
        for s in day.stops:
            if s.place.category != "landmark":
                continue
            opts = swap_options(it, SwapRequest(version=1, day_index=d_i, stop_order=s.order), catalog)
            same = [c.place.category == "landmark" for c in opts]
            assert opts and same == sorted(same, reverse=True)  # landmarks listed first
            day_has_mall = any(x.place.category == "malls" for x in day.stops if x.order != s.order)
            assert not day_has_mall or all(c.place.category != "malls" for c in opts)
            return
    raise AssertionError("no landmark in plan")


def test_apply_swap_replaces_stop_and_bumps_version(catalog):
    it = plan(catalog)
    last = len(it.days[0].stops) - 1  # dinner: meals always have nearby options
    stop = it.days[0].stops[last]
    pick = swap_options(it, SwapRequest(version=1, day_index=0, stop_order=last), catalog)[0]
    new = apply_swap(it, SwapApply(version=1, day_index=0, stop_order=last, new_place_id=pick.place.id),
                     catalog, EstimateRouter(), CALAMBA)
    assert new.version == 2
    assert new.days[0].stops[last].place.id == pick.place.id != stop.place.id
    assert new.days[1] == it.days[1]


def test_apply_swap_rejects_place_already_in_plan(catalog):
    it = plan(catalog)
    other = it.days[1].stops[0].place.id
    with pytest.raises(SwapError):
        apply_swap(it, SwapApply(version=1, day_index=0, stop_order=0, new_place_id=other),
                   catalog, EstimateRouter(), CALAMBA)


# ---- Alli 2026-11-18: walk-in places only. Walk-in resorts are public; private ones are kept apart ----

def test_seed_keeps_walk_in_resorts_and_moves_private_ones_out(seed):
    place_names = {p.name for p in seed.places}
    # Alli's Sheet review, Nov 18 2026
    assert {"La Vista Pansol", "Sol Y Viento", "Herbal Resort", "Grace Land Resort", "88 Spa & Resort"} <= place_names
    venues = {v.name: v for v in seed.venues}
    assert venues["Amarhi Private Resort"].walk_in == "no"
    assert venues["Blusyl Resort"].walk_in == "no"  # Alli overrode the website rule
    assert venues["Wonder Island Resort"].walk_in_reason == "rule:boat_access_only"  # car-only beta
    assert all(v.walk_in != "yes" or v.walk_in_reason == "rule:boat_access_only" for v in seed.venues)
    assert not ({p.id for p in seed.places} & {v.id for v in seed.venues})


def test_walk_in_rule():
    from app.places.models import WalkIn
    from app.places.rules import walk_in
    assert walk_in("Some Resort", {}, curated=True)[0] is WalkIn.YES
    assert walk_in("Zion Spring Private Resort", {"website": "x"}, curated=False)[0] is WalkIn.NO
    assert walk_in("Green Palm", {"opening_hours": "24/7"}, curated=False)[0] is WalkIn.NO
    assert walk_in("Herbal Resort", {"opening_hours": "7:00-18:00"}, curated=False)[0] is WalkIn.YES
    assert walk_in("Blusyl Resort", {"website": "http://blusyl.com"}, curated=False)[0] is WalkIn.YES
    assert walk_in("Villa Ana Resort", {}, curated=False)[0] is WalkIn.UNKNOWN
    # Alli's call in the Sheet's alli_walk_in column beats every rule.
    assert walk_in("Amarhi Private Resort", {"alli_walk_in": "walk-in"}, curated=False)[0] is WalkIn.YES
    assert walk_in("Blusyl Resort", {"website": "x", "alli_walk_in": "private"}, curated=False)[0] is WalkIn.NO


def test_hot_springs_plan_uses_walk_in_resorts_only(catalog, seed):
    private = {v.id for v in seed.venues}
    it = plan(catalog, days=4, interests={"hot_springs", "parks"})
    stops = [s for d in it.days for s in d.stops]
    assert any(s.place.category == "hot_springs" for s in stops)
    assert not ({s.place.id for s in stops} & private)
    for d_i, day in enumerate(it.days):
        assert sum(s.place.category == "hot_springs" for s in day.stops) <= 1
        for s in day.stops:
            opts = swap_options(it, SwapRequest(version=1, day_index=d_i, stop_order=s.order), catalog)
            assert not ({c.place.id for c in opts} & private)


def test_places_per_day_is_respected(catalog):
    for n in (1, 2, 3):
        it = plan(catalog, days=2, places_per_day=n)
        for d in it.days:
            sights = [s for s in d.stops if role_of(catalog.by_id[s.place.id]) is Role.SIGHT]
            assert 1 <= len(sights) <= n


def test_no_meal_stops_when_they_bring_food(catalog):
    it = plan(catalog, days=2, include_meals=False)
    for d in it.days:
        assert d.stops
        assert not [s for s in d.stops if role_of(catalog.by_id[s.place.id]) is Role.MEAL]


def test_day_starts_at_their_time(catalog):
    early = plan(catalog, days=1, start_time=time(6, 30))
    late = plan(catalog, days=1, start_time=time(10, 0))
    assert early.days[0].stops[0].arrive < time(7, 30)
    assert late.days[0].stops[0].arrive >= time(10, 0)


def test_start_time_outside_hours_is_rejected():
    with pytest.raises(ValueError):
        intake(start_time=time(14, 0))


def test_one_day_trip(catalog):
    it = plan(catalog, days=1)
    assert len(it.days) == 1 and it.intake.end_date == it.intake.start_date


def test_short_days_spread_into_the_afternoon(catalog):
    for meals in (True, False):
        it = plan(catalog, days=1, places_per_day=2, include_meals=meals)
        sights = [s for s in it.days[0].stops if role_of(catalog.by_id[s.place.id]) is Role.SIGHT]
        assert len(sights) == 2
        assert sights[0].arrive < time(12, 0) <= sights[1].arrive, it.days[0].stops


def test_swap_keeps_the_afternoon_start(catalog):
    it = plan(catalog, days=1, places_per_day=2, include_meals=False)
    day = it.days[0]
    opts = swap_options(it, SwapRequest(version=1, day_index=0, stop_order=0), catalog)
    new = apply_swap(it, SwapApply(version=1, day_index=0, stop_order=0, new_place_id=opts[0].place.id),
                     catalog, EstimateRouter(), CALAMBA)
    assert new.days[0].stops[1].arrive >= time(13, 0) and day.stops[1].arrive >= time(13, 0)


def test_generated_time_works_without_a_time_zone_list(monkeypatch):
    import zoneinfo

    def missing(key):
        raise zoneinfo.ZoneInfoNotFoundError(key)

    monkeypatch.setattr("app.regions.ZoneInfo", missing)
    assert CALAMBA.now().utcoffset().total_seconds() == 8 * 3600
