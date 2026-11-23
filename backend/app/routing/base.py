from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from ..schema import LatLng


@dataclass(frozen=True)
class Drive:
    """One free-flow car trip. Traffic factors are applied by the planner."""

    distance_m: int
    duration_s: int
    geometry: str  # polyline6


class Router(Protocol):
    name: Literal["osrm", "estimate"]

    def drive(self, a: LatLng, b: LatLng) -> Drive: ...
