"""Turn raw OSM tags into our place fields. Pure functions, no I/O."""

from __future__ import annotations

from ..schema import AccessStatus, Interest
from .models import Category

# (osm_key, osm_value) -> (category, outdoor). Only these features are imported.
KIND_MAP: dict[tuple[str, str], tuple[Category, bool]] = {
    ("tourism", "museum"): ("landmark", False),
    ("tourism", "attraction"): ("landmark", True),
    ("tourism", "viewpoint"): ("landmark", True),
    ("tourism", "zoo"): (Interest.PARKS, True),
    ("historic", "monument"): ("landmark", True),
    ("historic", "memorial"): ("landmark", True),
    ("amenity", "place_of_worship"): ("landmark", False),
    ("leisure", "park"): (Interest.PARKS, True),
    ("leisure", "garden"): (Interest.PARKS, True),
    ("leisure", "nature_reserve"): (Interest.PARKS, True),
    ("leisure", "water_park"): (Interest.HOT_SPRINGS, True),
    ("leisure", "resort"): (Interest.HOT_SPRINGS, True),
    ("natural", "hot_spring"): (Interest.HOT_SPRINGS, True),
    ("natural", "waterfall"): (Interest.WATERFALLS, True),
    ("waterway", "waterfall"): (Interest.WATERFALLS, True),
    ("landuse", "farmland"): (Interest.FARMS, True),
    ("tourism", "farm"): (Interest.FARMS, True),
    ("amenity", "restaurant"): ("other", False),  # refined by cuisine below
    ("amenity", "fast_food"): ("other", False),
    ("amenity", "cafe"): (Interest.CAFES, False),
    ("shop", "bakery"): ("other", False),
    ("amenity", "marketplace"): (Interest.MALLS, False),
    ("shop", "mall"): (Interest.MALLS, False),
    ("shop", "department_store"): (Interest.MALLS, False),
    ("tourism", "hotel"): ("other", False),
    ("tourism", "guest_house"): ("other", False),
    ("leisure", "sports_centre"): ("other", False),
    ("leisure", "golf_course"): ("other", True),
    ("amenity", "cinema"): ("other", False),
}
IMPORT_KEYS = frozenset(k for k, _ in KIND_MAP)

FILIPINO_CUISINES = frozenset({"filipino", "regional", "local", "bulalo", "lechon"})
SEAFOOD_CUISINES = frozenset({"seafood", "fish"})

_WHEELCHAIR = {"yes": AccessStatus.YES, "designated": AccessStatus.YES,
               "limited": AccessStatus.LIMITED, "no": AccessStatus.NO}


def classify(tags: dict[str, str]) -> tuple[str, str, Category, bool] | None:
    """Return (osm_key, osm_value, category, outdoor), or None to skip the feature."""
    if not tags.get("name", "").strip():
        return None  # unnamed features are not useful to travellers
    for key in ("tourism", "historic", "leisure", "natural", "waterway", "amenity", "shop", "landuse"):
        value = tags.get(key)
        if value and (key, value) in KIND_MAP:
            category, outdoor = KIND_MAP[(key, value)]
            if value in ("restaurant", "fast_food"):
                category = _food_category(tags.get("cuisine", ""))
            return key, value, category, outdoor
    return None


def _food_category(cuisine: str) -> Category:
    parts = {c.strip().lower() for c in cuisine.split(";") if c.strip()}
    if parts & SEAFOOD_CUISINES:
        return Interest.SEAFOOD
    if parts & FILIPINO_CUISINES:
        return Interest.TRADITIONAL_FOOD
    return "other"


def wheelchair(tags: dict[str, str]) -> AccessStatus:
    return _WHEELCHAIR.get(tags.get("wheelchair", "").lower(), AccessStatus.UNKNOWN)


def website(tags: dict[str, str]) -> str | None:
    for key in ("website", "contact:website", "contact:facebook", "facebook"):
        if tags.get(key):
            return tags[key][:300]
    return None
