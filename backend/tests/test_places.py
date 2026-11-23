import pytest
from pydantic import ValidationError

from app.places import matching, merge, normalize, rules
from app.places.models import OsmRecord, PlaceStatus, Submission
from app.places.osm_import import records_from_features
from app.schema import AccessStatus, Interest, LatLng, RegionId

CAL = RegionId.CALAMBA


def osm(ref="node/1", name="Rizal Shrine", lat=14.2134, lng=121.1668, **tags):
    tags = {"name": name, "tourism": "museum", **tags}
    return OsmRecord(osm_ref=ref, region=CAL, name=name, osm_key="tourism",
                     osm_value=tags["tourism"], coords=LatLng(lat=lat, lng=lng), tags=tags)


# --- normalize -------------------------------------------------------------
def test_unnamed_feature_skipped():
    assert normalize.classify({"amenity": "restaurant"}) is None


def test_unsupported_feature_skipped():
    assert normalize.classify({"name": "Shell", "amenity": "fuel"}) is None


def test_restaurant_category_from_cuisine():
    assert normalize.classify({"name": "Samaral", "amenity": "restaurant",
                               "cuisine": "seafood;filipino"})[2] is Interest.SEAFOOD
    assert normalize.classify({"name": "Bulalo sa Banga", "amenity": "restaurant",
                               "cuisine": "filipino"})[2] is Interest.TRADITIONAL_FOOD
    assert normalize.classify({"name": "Ramen", "amenity": "restaurant"})[2] == "other"


def test_water_park_is_hot_springs_and_outdoor():
    _, _, cat, outdoor = normalize.classify({"name": "La Vista", "leisure": "water_park"})
    assert cat is Interest.HOT_SPRINGS and outdoor


def test_wheelchair_values():
    assert normalize.wheelchair({"wheelchair": "designated"}) is AccessStatus.YES
    assert normalize.wheelchair({"wheelchair": "maybe"}) is AccessStatus.UNKNOWN


# --- rules -----------------------------------------------------------------
def test_chain_by_name_and_brand():
    assert rules.is_chain("Jollibee", {})
    assert rules.is_chain("Some Shop", {"brand": "X"})
    assert not rules.is_chain("Tudings", {})


@pytest.mark.parametrize("name,kind,tags,want", [
    ("Pool #3", "swimming_pool", {}, PlaceStatus.HIDDEN),
    ("Villa X", "water_park", {"access": "private"}, PlaceStatus.HIDDEN),
    ("Rizal Shrine", "museum", {}, PlaceStatus.PENDING),
    ("Tudings", "restaurant", {}, PlaceStatus.LISTED),
])
def test_auto_status(name, kind, tags, want):
    assert rules.auto_status(name, kind, tags)[0] is want


def test_chain_cannot_be_featured():
    with pytest.raises(ValueError):
        rules.check_featured_allowed(chain=True)


# --- merge -----------------------------------------------------------------
def test_new_place_created_with_rule_status():
    res = merge.merge_run({}, [osm()])
    assert res.added == 1
    p = res.upserts[0]
    assert p.id == "osm:node/1" and p.status is PlaceStatus.PENDING


def test_refresh_respects_overrides():
    p = merge.place_from_osm(osm(opening_hours="Mo-Su 08:00-16:00"))
    p = p.model_copy(update={"opening_hours": "Tu-Su 08:00-17:00",
                             "overrides": {"opening_hours": "owner"}})
    res = merge.merge_run({"node/1": p}, [osm(name="Museo ni Rizal", opening_hours="24/7")])
    new = res.upserts[0]
    assert new.name == "Museo ni Rizal"               # OSM-owned, not overridden
    assert new.opening_hours == "Tu-Su 08:00-17:00"   # owner's value kept


def test_person_status_survives_refresh():
    p = merge.place_from_osm(osm()).model_copy(
        update={"status": PlaceStatus.FEATURED, "overrides": {"status": "alli"}})
    res = merge.merge_run({"node/1": p}, [osm(name="Rizal Shrine Museum")])
    assert res.upserts[0].status is PlaceStatus.FEATURED


def test_known_wheelchair_not_erased_by_unknown():
    p = merge.place_from_osm(osm()).model_copy(update={"wheelchair": AccessStatus.LIMITED})
    res = merge.merge_run({"node/1": p}, [osm(name="Rizal Shrine 2")])
    assert res.upserts[0].wheelchair is AccessStatus.LIMITED


def test_missing_place_flagged_not_deleted():
    p = merge.place_from_osm(osm())
    res = merge.merge_run({"node/1": p}, [])
    assert res.missing == ["osm:node/1"] and res.upserts[0].possibly_closed


def test_unchanged_place_not_rewritten():
    p = merge.place_from_osm(osm())
    assert merge.merge_run({"node/1": p}, [osm()]).upserts == []


# --- import ----------------------------------------------------------------
def test_import_filters_bbox_and_duplicates():
    feats = [
        ("node/1", {"name": "Rizal Shrine", "tourism": "museum"}, 14.2134, 121.1668),
        ("node/1", {"name": "Rizal Shrine", "tourism": "museum"}, 14.2134, 121.1668),
        ("node/2", {"name": "Pagsanjan Falls", "waterway": "waterfall"}, 14.2626, 121.50),
        ("node/3", {"amenity": "restaurant"}, 14.20, 121.16),
    ]
    out = list(records_from_features(feats, CAL))
    assert [r.osm_ref for r in out] == ["node/1"]


# --- matching --------------------------------------------------------------
def sub(name="Tuding's Original Porkchop", lat=14.19534, lng=121.14326, **kw):
    return Submission(region=CAL, business_name=name, category="other",
                      coords=LatLng(lat=lat, lng=lng), contact_email="owner@example.com", **kw)


def test_submission_matches_nearby_similar_name():
    place = merge.place_from_osm(osm(ref="way/109338570", name="Tudings",
                                     lat=14.1953305, lng=121.1432506, tourism="attraction"))
    hit = matching.best_match(sub(name="Tudings Porkchop"), [place])
    assert hit is not None and hit[0].id == "osm:way/109338570"


def test_submission_far_away_is_new():
    place = merge.place_from_osm(osm(name="Tudings", lat=14.21, lng=121.16, tourism="attraction"))
    assert matching.best_match(sub(name="Tudings"), [place]) is None


def test_owner_data_protected_after_approval():
    place = merge.place_from_osm(osm())
    upd = matching.apply_owner_data(place, sub(opening_hours="Mo-Su 09:00-17:00",
                                               wheelchair=AccessStatus.YES))
    assert upd.overrides == {"opening_hours": "owner", "wheelchair": "owner"}
    assert upd.wheelchair is AccessStatus.YES


def test_bad_email_rejected():
    with pytest.raises(ValidationError):
        Submission(region=CAL, business_name="X Shop", category="other",
                   coords=LatLng(lat=14.2, lng=121.16), contact_email="nope")


def test_distance_is_sane():
    d = matching.distance_m(LatLng(lat=14.2134, lng=121.1668), LatLng(lat=14.2134, lng=121.1678))
    assert 100 < d < 115
