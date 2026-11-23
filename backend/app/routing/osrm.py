"""OSRM /route client. One request per leg, cached for the life of the router."""

from __future__ import annotations

from typing import Literal

import httpx

from ..schema import LatLng
from .base import Drive

PARKING_S = 120  # OSRM ends at the road; add time to park and walk in


class RoutingUnavailable(RuntimeError):
    """OSRM did not answer or had no road route. The caller falls back to estimates."""


class OsrmRouter:
    name: Literal["osrm"] = "osrm"

    def __init__(self, base_url: str, client: httpx.Client):
        self._base = base_url.rstrip("/")
        self._client = client
        self._cache: dict[tuple[float, float, float, float], Drive] = {}

    def drive(self, a: LatLng, b: LatLng) -> Drive:
        key = (round(a.lat, 5), round(a.lng, 5), round(b.lat, 5), round(b.lng, 5))
        if key not in self._cache:
            self._cache[key] = self._fetch(a, b)
        return self._cache[key]

    def _fetch(self, a: LatLng, b: LatLng) -> Drive:
        url = f"{self._base}/route/v1/driving/{a.lng},{a.lat};{b.lng},{b.lat}"
        try:
            r = self._client.get(url, params={"overview": "full", "geometries": "polyline6"})
            r.raise_for_status()
            body = r.json()
        except (httpx.HTTPError, ValueError) as e:
            raise RoutingUnavailable(str(e)) from e
        if body.get("code") != "Ok" or not body.get("routes"):
            raise RoutingUnavailable(f"osrm: {body.get('code')}")
        route = body["routes"][0]
        return Drive(
            distance_m=round(route["distance"]),
            duration_s=round(route["duration"]) + PARKING_S,
            geometry=route["geometry"],
        )
