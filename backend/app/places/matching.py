"""Match a business-owner submission to a place we already have."""

from __future__ import annotations

import math
import re
import unicodedata
from collections.abc import Sequence
from difflib import SequenceMatcher

from ..schema import LatLng
from .models import PlaceRecord, PrivateVenue, Submission

MATCH_RADIUS_M = 100       # same business is assumed to be this close
MATCH_MIN_SCORE = 0.80     # 0..1 name similarity after cleaning

_FILLER = re.compile(
    r"\b(the|resto|restaurant|bar|cafe|coffee|shop|store|calamba|branch|inc|corp)\b"
)


def distance_m(a: LatLng, b: LatLng) -> float:
    """Great-circle distance (haversine). Accurate to well under 1 m at city scale."""
    r = 6_371_000
    p1, p2 = math.radians(a.lat), math.radians(b.lat)
    dp, dl = p2 - p1, math.radians(b.lng - a.lng)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def clean_name(name: str) -> str:
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    s = s.replace("'", "").replace("’", "")
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = _FILLER.sub(" ", s)
    return " ".join(s.split())


def name_score(a: str, b: str) -> float:
    ca, cb = clean_name(a), clean_name(b)
    if not ca or not cb:
        return 0.0
    ratio = SequenceMatcher(None, ca, cb).ratio()
    # Owners often add words ("Tudings" vs "Tudings Porkchop"): if every word of
    # the shorter name is in the longer one, treat it as a strong match.
    ta, tb = set(ca.split()), set(cb.split())
    if ta <= tb or tb <= ta:
        ratio = max(ratio, 0.9)
    return ratio


def best_match(
    sub: Submission, nearby: Sequence[PlaceRecord | PrivateVenue],
) -> tuple[PlaceRecord | PrivateVenue, float] | None:
    """Closest good match within MATCH_RADIUS_M, or None if it looks new.

    `nearby` should already be filtered by the DB (ST_DWithin) to keep this cheap.
    """
    best: tuple[PlaceRecord | PrivateVenue, float] | None = None
    for place in nearby:
        if place.region != sub.region:
            continue
        if distance_m(sub.coords, place.coords) > MATCH_RADIUS_M:
            continue
        score = name_score(sub.business_name, place.name)
        if score >= MATCH_MIN_SCORE and (best is None or score > best[1]):
            best = (place, score)
    return best


def apply_owner_data(place: PlaceRecord, sub: Submission) -> PlaceRecord:
    """After a person approves a matched submission: owner data fills the gaps
    and is protected from future OSM refreshes."""
    updates: dict = {}
    overrides = dict(place.overrides)
    if sub.opening_hours:
        updates["opening_hours"] = sub.opening_hours
        overrides["opening_hours"] = "owner"
    if sub.wheelchair.value != "unknown":
        updates["wheelchair"] = sub.wheelchair
        overrides["wheelchair"] = "owner"
    if sub.website:
        updates["website"] = sub.website
        overrides["website"] = "owner"
    updates["overrides"] = overrides
    return place.model_copy(update=updates)
