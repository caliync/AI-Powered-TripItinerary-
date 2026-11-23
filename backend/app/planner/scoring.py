"""How much a place suits this trip. Higher is better; only the order matters."""

from __future__ import annotations

from ..places.matching import distance_m
from ..places.models import PlaceRecord, PlaceStatus
from ..schema import AccessNeed, Interest, LatLng, TripIntake
from .catalog import Role, is_curated

# Sight categories offered when the traveller picks no interests ("a mix").
MIX = frozenset({"landmark", Interest.PARKS, Interest.HOT_SPRINGS, "other"})
ALWAYS = frozenset({"landmark", Interest.PARKS, "other"})  # core sightseeing


def sight_allowed(p: PlaceRecord, intake: TripIntake) -> bool:
    if not intake.interests:
        return p.category in MIX
    return p.category in ALWAYS or p.category in intake.interests


def sight_score(p: PlaceRecord, intake: TripIntake) -> float:
    s = {PlaceStatus.FEATURED: 5.0}.get(p.status, 3.0 if is_curated(p) else 1.0)
    if p.category in intake.interests:
        s += 2
    if p.is_chain:
        s -= 1
    needs = intake.access_needs
    if AccessNeed.SENSORY_FRIENDLY in needs and p.category in (Interest.MALLS, Interest.HOT_SPRINGS):
        s -= 2  # crowds and noise
    if AccessNeed.MINIMAL_WALKING in needs and p.category == Interest.PARKS:
        s -= 1
    return s


def meal_score(p: PlaceRecord, intake: TripIntake) -> float:
    s = 3.0 if is_curated(p) else 0.0
    if p.category in (Interest.TRADITIONAL_FOOD, Interest.SEAFOOD):
        s += 1
        if p.category in intake.interests:
            s += 2
    if not p.is_chain:
        s += 2  # beta rule: local businesses first
    return s


def score(p: PlaceRecord, role: Role, intake: TripIntake) -> float:
    return sight_score(p, intake) if role is Role.SIGHT else meal_score(p, intake)


def km(a: LatLng, b: LatLng) -> float:
    return distance_m(a, b) / 1000
