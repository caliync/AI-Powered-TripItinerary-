"""Encoded polyline, precision 6 (what OSRM returns with geometries=polyline6)."""

from __future__ import annotations

from ..schema import LatLng

_FACTOR = 1e6


def encode(points: list[LatLng]) -> str:
    out: list[str] = []
    prev_lat = prev_lng = 0
    for p in points:
        lat, lng = round(p.lat * _FACTOR), round(p.lng * _FACTOR)
        for delta in (lat - prev_lat, lng - prev_lng):
            v = ~(delta << 1) if delta < 0 else delta << 1
            while v >= 0x20:
                out.append(chr((0x20 | (v & 0x1F)) + 63))
                v >>= 5
            out.append(chr(v + 63))
        prev_lat, prev_lng = lat, lng
    return "".join(out)


def decode(s: str) -> list[LatLng]:
    pts: list[LatLng] = []
    i = lat = lng = 0
    while i < len(s):
        vals = []
        for _ in range(2):
            shift = result = 0
            while True:
                b = ord(s[i]) - 63
                i += 1
                result |= (b & 0x1F) << shift
                shift += 5
                if b < 0x20:
                    break
            vals.append(~(result >> 1) if result & 1 else result >> 1)
        lat += vals[0]
        lng += vals[1]
        pts.append(LatLng(lat=lat / _FACTOR, lng=lng / _FACTOR))
    return pts
