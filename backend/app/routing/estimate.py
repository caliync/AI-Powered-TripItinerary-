"""Fallback when OSRM can't be reached. Rough town driving, clearly marked as an estimate."""

from __future__ import annotations

from typing import Literal

from ..places.matching import distance_m
from ..schema import LatLng
from .base import Drive
from .polyline import encode

DETOUR = 1.35        # roads are longer than a straight line
TOWN_SPEED_KMH = 25  # PLACEHOLDER: calibrate against OSRM once reachable
PARKING_S = 120      # finding parking, walking to the entrance


class EstimateRouter:
    name: Literal["estimate"] = "estimate"

    def drive(self, a: LatLng, b: LatLng) -> Drive:
        d = distance_m(a, b) * DETOUR
        seconds = d / (TOWN_SPEED_KMH * 1000 / 3600) + (PARKING_S if d > 0 else 0)
        return Drive(distance_m=round(d), duration_s=round(seconds), geometry=encode([a, b]))
