from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api import create_app
from app.config import BACKEND_DIR, Settings

from .conftest import HOTEL_MARCIANO

BODY = {
    "stay": {"label": "Hotel Marciano, Real", "coords": None},
    "start_date": "2026-12-05", "end_date": "2026-12-06",
    "group": "duo", "budget": "mid", "access_needs": [], "interests": ["parks"],
}


@pytest.fixture
def client(tmp_db: Path):
    # No network in tests: no OSRM (estimates) and no Nominatim (local stay match only).
    s = Settings(db_path=tmp_db, seed_dir=BACKEND_DIR / "data", osrm_url=None, nominatim_url=None)
    with TestClient(create_app(s)) as c:
        yield c


def test_generate_then_get(client):
    r = client.post("/api/v1/itinerary/generate", json=BODY)
    assert r.status_code == 201, r.text
    it = r.json()
    assert it["providers"]["routing"] == "estimate"
    assert len(it["days"]) == 2
    assert client.get(f"/api/v1/itinerary/{it['id']}").json() == it


def test_stay_found_from_local_hotels(client):
    it = client.post("/api/v1/itinerary/generate", json=BODY).json()
    assert abs(it["stay_coords"]["lat"] - HOTEL_MARCIANO["lat"]) < 0.002


def test_unknown_stay_is_a_clear_422(client):
    r = client.post("/api/v1/itinerary/generate", json={**BODY, "stay": {"label": "Nowhere Inn"}})
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "stay_not_found"


def test_invalid_intake_uses_error_shape(client):
    r = client.post("/api/v1/itinerary/generate", json={**BODY, "end_date": "2026-12-30"})
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "invalid_input"


def test_missing_plan_is_404(client):
    r = client.get("/api/v1/itinerary/00000000-0000-4000-8000-000000000000")
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "not_found"


def test_swap_flow_and_stale_version(client):
    it = client.post("/api/v1/itinerary/generate", json=BODY).json()
    base = f"/api/v1/itinerary/{it['id']}"
    last = len(it["days"][0]["stops"]) - 1  # dinner: meals always have nearby options
    opts = client.post(f"{base}/swap", json={"version": 1, "day_index": 0, "stop_order": last}).json()
    assert opts
    body = {"version": 1, "day_index": 0, "stop_order": last, "new_place_id": opts[0]["place"]["id"]}
    r = client.post(f"{base}/swap/apply", json=body)
    assert r.status_code == 200 and r.json()["version"] == 2
    assert client.post(f"{base}/swap/apply", json=body).status_code == 409


def test_business_submission(client):
    r = client.post("/api/v1/places/submissions", json={
        "region": "calamba", "business_name": "Tudings Porkchop", "category": "traditional_food",
        "coords": {"lat": 14.19533, "lng": 121.14325}, "opening_hours": None, "wheelchair": "limited",
        "website": None, "contact_email": "owner@example.com",
    })
    assert r.status_code == 202 and r.json() == {"status": "pending"}


def test_business_outside_region(client):
    r = client.post("/api/v1/places/submissions", json={
        "region": "calamba", "business_name": "Far Away Cafe", "category": "cafes",
        "coords": {"lat": 14.6, "lng": 121.0}, "wheelchair": "unknown", "contact_email": "a@b.co",
    })
    assert r.status_code == 422


def test_stay_at_a_private_resort_is_still_found(client):
    r = client.post("/api/v1/itinerary/generate", json={**BODY, "stay": {"label": "Amarhi Private Resort"}})
    assert r.status_code == 201, r.text
    stops = {s["place"]["name"] for d in r.json()["days"] for s in d["stops"]}
    assert "Amarhi Private Resort" not in stops


def test_old_database_has_private_resorts_moved_out(tmp_db):
    from app.db import Store
    from app.places.models import PlaceRecord
    from app.schema import RegionId
    store = Store(tmp_db)  # simulate a database seeded before the split
    old = [("osm:node/11795447391", "Amarhi Private Resort"), ("osm:way/170221744", "La Vista Pansol")]
    store.upsert_places([PlaceRecord(id=pid, osm_ref=pid[4:], region="calamba", name=name, category="hot_springs",
                                     kind="water_park", coords={"lat": 14.18, "lng": 121.19}, status="listed")
                         for pid, name in old], {})
    s = Settings(db_path=tmp_db, seed_dir=BACKEND_DIR / "data", osrm_url=None, nominatim_url=None)
    with TestClient(create_app(s)):
        pass
    places, _ = store.places(RegionId.CALAMBA)
    venues = {v.id for v in store.venues(RegionId.CALAMBA)}
    assert "osm:node/11795447391" in venues and "osm:node/11795447391" not in {p.id for p in places}
    assert "osm:way/170221744" in {p.id for p in places}  # walk-in resort stays plannable


def test_stay_suggestions_while_typing(client):
    names = [s["name"] for s in client.get("/api/v1/stays/suggest", params={"q": "Mar"}).json()]
    assert names[0] == "Hotel Marciano"


def test_stay_suggestions_forgive_spelling(client):
    names = [s["name"] for s in client.get("/api/v1/stays/suggest", params={"q": "Hotel Merciano"}).json()]
    assert names[0] == "Hotel Marciano"


def test_stay_suggestions_need_two_letters(client):
    assert client.get("/api/v1/stays/suggest", params={"q": "m"}).json() == []


def test_typed_budget_and_interests_are_accepted(client):
    body = {**BODY, "budget_php": 6000, "interests_text": "waterfalls, kape"}
    assert client.post("/api/v1/itinerary/generate", json=body).status_code == 201


def test_day_choices_give_options_for_each_stop(client):
    it = client.post("/api/v1/itinerary/generate", json=BODY).json()
    r = client.get(f"/api/v1/itinerary/{it['id']}/days/0/choices")
    assert r.status_code == 200, r.text
    choices = r.json()
    assert [c["stop_order"] for c in choices] == list(range(len(it["days"][0]["stops"])))
    offered = [o["place"]["id"] for c in choices for o in c["options"]]
    assert offered
    for c in choices:
        ids = [o["place"]["id"] for o in c["options"]]
        assert len(ids) == len(set(ids))
    in_plan = {s["place"]["id"] for d in it["days"] for s in d["stops"]}
    assert not in_plan & set(offered)
    assert all(len(c["options"]) <= 3 for c in choices)
    assert client.get(f"/api/v1/itinerary/{it['id']}/days/9/choices").status_code == 404


ONE_DAY = {**BODY, "end_date": "2026-12-05", "places_per_day": 3}


def _recs(client, it, day=0):
    r = client.get(f"/api/v1/itinerary/{it['id']}/days/{day}/recommendations")
    assert r.status_code == 200, r.text
    return r.json()


def test_recommendations_are_many_unused_sights(client):
    it = client.post("/api/v1/itinerary/generate", json=ONE_DAY).json()
    recs = _recs(client, it)
    assert len(recs) >= 6
    ids = [r["place"]["id"] for r in recs]
    assert len(ids) == len(set(ids))
    assert not set(ids) & {s["place"]["id"] for d in it["days"] for s in d["stops"]}
    assert client.get(f"/api/v1/itinerary/{it['id']}/days/9/recommendations").status_code == 404


@pytest.mark.parametrize("part", ["morning", "afternoon", "evening"])
def test_add_a_place_to_each_part_of_the_day(client, part):
    it = client.post("/api/v1/itinerary/generate", json=ONE_DAY).json()
    base = f"/api/v1/itinerary/{it['id']}"
    new = _recs(client, it)[0]["place"]["id"]
    r = client.post(f"{base}/stops/add", json={"version": it["version"], "day_index": 0,
                                                "new_place_id": new, "part": part})
    assert r.status_code == 200, r.text
    day = r.json()["days"][0]
    assert r.json()["version"] == it["version"] + 1
    assert len(day["stops"]) == len(it["days"][0]["stops"]) + 1
    added = next(s for s in day["stops"] if s["place"]["id"] == new)
    hour = int(added["arrive"][:2])
    assert {"morning": hour < 12, "afternoon": 12 <= hour < 17, "evening": hour >= 17}[part]
    times = [s["arrive"] for s in day["stops"]]
    assert times == sorted(times)
    assert [s["order"] for s in day["stops"]] == list(range(len(day["stops"])))
    assert client.post(f"{base}/stops/add", json={"version": it["version"], "day_index": 0,
                                                   "new_place_id": new, "part": part}).status_code == 409


def test_remove_a_place_and_the_last_one_leaves_a_rest_day(client):
    it = client.post("/api/v1/itinerary/generate", json=ONE_DAY).json()
    base = f"/api/v1/itinerary/{it['id']}"
    version, stops = it["version"], it["days"][0]["stops"]
    gone = stops[0]["place"]["id"]
    r = client.post(f"{base}/stops/remove", json={"version": version, "day_index": 0, "stop_order": 0})
    assert r.status_code == 200, r.text
    left = r.json()["days"][0]["stops"]
    assert len(left) == len(stops) - 1 and gone not in [s["place"]["id"] for s in left]
    assert client.post(f"{base}/stops/remove", json={"version": version, "day_index": 0,
                                                      "stop_order": 0}).status_code == 409
    it2 = r.json()
    for _ in range(len(left)):
        it2 = client.post(f"{base}/stops/remove", json={"version": it2["version"], "day_index": 0,
                                                         "stop_order": 0}).json()
    assert it2["days"][0]["stops"] == []
    bad = client.post(f"{base}/stops/remove", json={"version": it2["version"], "day_index": 0, "stop_order": 0})
    assert bad.status_code == 422


def test_a_full_day_cannot_take_more_places(client):
    it = client.post("/api/v1/itinerary/generate", json={**ONE_DAY, "places_per_day": 6}).json()
    base = f"/api/v1/itinerary/{it['id']}"
    for _ in range(4):
        new = _recs(client, it)[0]["place"]["id"]
        r = client.post(f"{base}/stops/add", json={"version": it["version"], "day_index": 0,
                                                    "new_place_id": new, "part": "morning"})
        if r.status_code != 200:
            assert r.status_code == 422
            return
        it = r.json()
    pytest.fail("the day never filled up")


def test_times_are_on_five_minutes(client):
    it = client.post("/api/v1/itinerary/generate", json=ONE_DAY).json()
    for s in it["days"][0]["stops"]:
        assert int(s["arrive"][3:5]) % 5 == 0, s["arrive"]


def test_meal_reason_never_names_a_removed_stop(client):
    it = client.post("/api/v1/itinerary/generate", json=ONE_DAY).json()
    base = f"/api/v1/itinerary/{it['id']}"
    stops = it["days"][0]["stops"]
    lunch = next(s for s in stops if s["reason"].lower().startswith("lunch"))
    before = stops[lunch["order"] - 1]["place"]["name"]
    assert before in lunch["reason"]
    out = client.post(f"{base}/stops/remove", json={"version": it["version"], "day_index": 0,
                                                     "stop_order": lunch["order"] - 1}).json()
    new_lunch = next(s for s in out["days"][0]["stops"] if s["reason"].lower().startswith("lunch"))
    assert before not in new_lunch["reason"]


def test_a_removed_meal_can_be_put_back(client):
    it = client.post("/api/v1/itinerary/generate", json=ONE_DAY).json()
    base = f"/api/v1/itinerary/{it['id']}"
    stops = it["days"][0]["stops"]
    dinner = stops[-1]
    assert dinner["reason"].lower().startswith("dinner")
    out = client.post(f"{base}/stops/remove", json={"version": it["version"], "day_index": 0,
                                                     "stop_order": dinner["order"]}).json()
    back = client.post(f"{base}/stops/add", json={"version": out["version"], "day_index": 0, "part": "evening",
                                                   "new_place_id": dinner["place"]["id"], "meal": "dinner"})
    assert back.status_code == 200, back.text
    last = back.json()["days"][0]["stops"][-1]
    assert last["place"]["id"] == dinner["place"]["id"] and last["reason"].lower().startswith("dinner")
