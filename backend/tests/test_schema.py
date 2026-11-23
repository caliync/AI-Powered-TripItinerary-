from datetime import UTC, date, datetime, time
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.regions import REGIONS, traffic_factor
from app.schema import (
    STAY_ID,
    DayPlan,
    Itinerary,
    Leg,
    LLMDayPicks,
    Place,
    RegionId,
    Stop,
    SwapRequest,
    TripIntake,
)

CALAMBA = REGIONS[RegionId.CALAMBA]


def intake(**kw):
    base = dict(
        stay={"label": "Hotel in Calamba", "coords": {"lat": 14.21, "lng": 121.16}},
        start_date=date(2026, 12, 1),
        end_date=date(2026, 12, 2),
        group="duo",
        budget="mid",
    )
    base.update(kw)
    return TripIntake.model_validate(base)


def place(pid="osm:node/1", **kw):
    base = dict(id=pid, name="Spot", coords={"lat": 14.2, "lng": 121.15}, category="parks", outdoor=True)
    base.update(kw)
    return Place.model_validate(base)


def leg(a, b, s=600):
    return Leg(from_id=a, to_id=b, distance_m=5000, duration_s=s, geometry="")


def day(d, ids, cluster=0):
    stops = [
        Stop(order=i, place=place(pid), arrive=time(8 + i, 0), depart=time(8 + i, 45), dwell_min=60, reason="r")
        for i, pid in enumerate(ids)
    ]
    chain = [STAY_ID, *ids, STAY_ID] if ids else []
    legs = [leg(a, b) for a, b in zip(chain, chain[1:])]
    return DayPlan(
        date=d, cluster_id=cluster, centroid={"lat": 14.2, "lng": 121.15}, radius_m=3000,
        stops=stops, legs=legs, total_travel_s=sum(l.duration_s for l in legs),
    )


# ---------- intake ----------
def test_valid_intake_defaults():
    t = intake()
    assert t.region is RegionId.CALAMBA
    assert t.allow_unverified_access is True
    assert t.trip_days == 2


def test_rejects_unknown_keys():
    with pytest.raises(ValidationError):
        intake(hacker="x")


def test_end_before_start_rejected():
    with pytest.raises(ValidationError):
        intake(start_date=date(2026, 12, 5), end_date=date(2026, 12, 1))


def test_trip_over_14_days_rejected():
    with pytest.raises(ValidationError):
        intake(end_date=date(2026, 12, 15))


@pytest.mark.parametrize("group,count,ok", [("group", 5, True), ("group", None, False), ("solo", 3, False)])
def test_group_count_rule(group, count, ok):
    if ok:
        intake(group=group, group_count=count)
    else:
        with pytest.raises(ValidationError):
            intake(group=group, group_count=count)


def test_unknown_interest_rejected():
    with pytest.raises(ValidationError):
        intake(interests=["casinos"])


# ---------- places ----------
@pytest.mark.parametrize("pid", ["gp:ChIJabc", "osm:node/abc", "node/1", ""])
def test_bad_place_ids_rejected(pid):
    with pytest.raises(ValidationError):
        place(pid)


# ---------- day loop ----------
def test_valid_loop():
    d = day(date(2026, 12, 1), ["osm:node/1", "osm:way/2"])
    assert d.legs[0].from_id == STAY_ID and d.legs[-1].to_id == STAY_ID


def test_legs_out_of_order_rejected():
    d = day(date(2026, 12, 1), ["osm:node/1", "osm:node/2"])
    bad = d.model_dump()
    bad["legs"][1], bad["legs"][2] = bad["legs"][2], bad["legs"][1]
    with pytest.raises(ValidationError):
        DayPlan.model_validate(bad)


def test_total_travel_mismatch_rejected():
    bad = day(date(2026, 12, 1), ["osm:node/1"]).model_dump()
    bad["total_travel_s"] += 1
    with pytest.raises(ValidationError):
        DayPlan.model_validate(bad)


def test_rest_day_has_no_legs():
    assert day(date(2026, 12, 1), []).legs == []


def test_more_than_8_stops_rejected():
    with pytest.raises(ValidationError):
        day(date(2026, 12, 1), [f"osm:node/{i}" for i in range(9)])


# ---------- itinerary ----------
def itinerary(days):
    return Itinerary(
        id=uuid4(), version=1, intake=intake(), stay_coords={"lat": 14.21, "lng": 121.16},
        days=days, generated_at=datetime.now(UTC),
    )


def test_valid_itinerary():
    itinerary([day(date(2026, 12, 1), ["osm:node/1"]), day(date(2026, 12, 2), ["osm:node/2"], 1)])


def test_same_place_on_two_days_rejected():
    with pytest.raises(ValidationError):
        itinerary([day(date(2026, 12, 1), ["osm:node/1"]), day(date(2026, 12, 2), ["osm:node/1"], 1)])


def test_missing_day_rejected():
    with pytest.raises(ValidationError):
        itinerary([day(date(2026, 12, 1), ["osm:node/1"])])


# ---------- swap ----------
@pytest.mark.parametrize("r,ok", [(3000, True), (5000, True), (2999, False), (5001, False)])
def test_swap_radius_locked(r, ok):
    args = dict(version=1, day_index=0, stop_order=0, radius_m=r)
    if ok:
        SwapRequest(**args)
    else:
        with pytest.raises(ValidationError):
            SwapRequest(**args)


# ---------- LLM output ----------
def test_llm_cannot_send_coords():
    with pytest.raises(ValidationError):
        LLMDayPicks.model_validate(
            {"day_index": 0, "picks": [{"place_id": "osm:node/1", "reason": "x", "lat": 1}]}
        )


def test_llm_invented_ids_detected():
    p = LLMDayPicks.model_validate({"day_index": 0, "picks": [{"place_id": "osm:node/99", "reason": "x"}]})
    assert p.unknown_ids({"osm:node/1"}) == ["osm:node/99"]


# ---------- region ----------
def test_calamba_contains_center_and_factor():
    assert CALAMBA.bbox.contains(CALAMBA.center)
    assert traffic_factor(CALAMBA, time(8, 0)) > 1.0
    assert traffic_factor(CALAMBA, time(12, 0)) == 1.0


def test_json_schema_exports():
    # The schema the forced LLM tool call uses, and what openapi-typescript reads.
    s = LLMDayPicks.model_json_schema()
    assert s["additionalProperties"] is False
