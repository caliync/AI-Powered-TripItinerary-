"""Find the coordinates of where the traveller is staying.

Order: coordinates sent by the client, then our own hotels and guest houses
(fast, no network), then Nominatim limited to the region's box.
"""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Protocol

import httpx

from .places.matching import clean_name, name_score
from .places.models import PlaceRecord, PrivateVenue
from .regions import RegionConfig
from .schema import LatLng, StayLocation

# Travellers often stay at a resort, so private venues count when finding the stay.
STAY_KINDS = frozenset({"hotel", "guest_house", "water_park", "resort", "swimming_pool", "curated"})
LOCAL_MATCH_MIN = 0.85
FUZZY_MIN = 0.75  # how close a misspelt word must be to suggest a stay
# Hotels first when several names fit: they are where most travellers stay.
KIND_ORDER = {"hotel": 0, "resort": 1, "guest_house": 2, "curated": 3, "water_park": 4, "swimming_pool": 5}


class StayNotFound(Exception):
    pass


class StayOutsideRegion(Exception):
    pass


class _Named(Protocol):
    name: str
    kind: str
    coords: LatLng


def _local_match(label: str, places: list[_Named]) -> LatLng | None:
    best: tuple[float, _Named] | None = None
    first_part = label.split(",")[0]  # "Hotel Marciano, Real" -> "Hotel Marciano"
    for p in places:
        if p.kind not in STAY_KINDS:
            continue
        score = max(name_score(label, p.name), name_score(first_part, p.name))
        if score >= LOCAL_MATCH_MIN and (best is None or score > best[0]):
            best = (score, p)
    return best[1].coords if best else None


def _words(text: str) -> list[str]:
    return clean_name(text).split()


def suggest_stays(query: str, places: list[PlaceRecord | PrivateVenue], limit: int = 6) -> list[_Named]:
    """Stays whose name fits what the traveller has typed so far.

    Every typed word must start a word of the name ("mar" finds "Hotel Marciano").
    If nothing fits, close spellings count too ("merciano" finds "Hotel Marciano").
    """
    typed = _words(query)
    if not typed or len(query.strip()) < 2:
        return []
    stays = [p for p in places if p.kind in STAY_KINDS]
    prefix = [p for p in stays if all(any(w.startswith(t) for w in _words(p.name)) for t in typed)]
    if prefix:
        prefix.sort(key=lambda p: (not _words(p.name)[0].startswith(typed[0]), KIND_ORDER.get(p.kind, 9),
                                   len(p.name), p.name))
        return prefix[:limit]
    scored = []
    for p in stays:
        words = _words(p.name)
        # each typed word scores against its closest word in the name; all of them must fit
        score = min(max(SequenceMatcher(None, t, w).ratio() for w in words) for t in typed) if words else 0.0
        if score >= FUZZY_MIN:
            scored.append((score, p))
    scored.sort(key=lambda x: (-x[0], x[1].name))
    return [p for _, p in scored[:limit]]


def _nominatim(label: str, region: RegionConfig, base_url: str, client: httpx.Client) -> LatLng | None:
    b = region.bbox
    try:
        r = client.get(f"{base_url.rstrip('/')}/search", params={
            "q": f"{label}, {region.name}, {region.province}", "format": "jsonv2", "limit": 1,
            "countrycodes": "ph", "bounded": 1, "viewbox": f"{b.west},{b.north},{b.east},{b.south}",
        })
        r.raise_for_status()
        hits = r.json()
    except (httpx.HTTPError, ValueError):
        return None
    if not hits:
        return None
    return LatLng(lat=float(hits[0]["lat"]), lng=float(hits[0]["lon"]))


def locate_stay(stay: StayLocation, region: RegionConfig, places: list[PlaceRecord | PrivateVenue],
                nominatim_url: str | None, client: httpx.Client) -> LatLng:
    coords = stay.coords or _local_match(stay.label, places)
    if coords is None and nominatim_url:
        coords = _nominatim(stay.label, region, nominatim_url, client)
    if coords is None:
        raise StayNotFound(stay.label)
    if not region.bbox.contains(coords):
        raise StayOutsideRegion(stay.label)
    return coords
