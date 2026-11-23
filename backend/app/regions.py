"""Per-city routing config. Beta: Calamba, Laguna. Add other Laguna cities here.

Values marked PLACEHOLDER are starting guesses to calibrate against real
OSRM runs and local knowledge before launch; they are not measured data.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from typing import Annotated
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field

from .schema import BBox, LatLng, RegionId, Strict


class PeakWindow(Strict):
    start: time
    end: time
    factor: Annotated[float, Field(ge=1.0, le=4.0)]  # multiplies OSRM free-flow time


class RegionConfig(Strict):
    id: RegionId
    name: str
    province: str
    bbox: BBox  # rejects stays outside the region
    center: LatLng
    search_radius_m: Annotated[int, Field(ge=1000, le=60000)]
    day_start: time
    day_end: time
    outdoor_window_end: time  # outdoor stops are scheduled before this
    peak_windows: tuple[PeakWindow, ...]
    timezone: str = "Asia/Manila"
    utc_offset_hours: int = 8  # used when the machine has no time zone list (Windows without tzdata)

    def now(self) -> datetime:
        """The current time in the region. Falls back to a fixed offset: the Philippines has no daylight saving."""
        try:
            return datetime.now(ZoneInfo(self.timezone))
        except ZoneInfoNotFoundError:
            return datetime.now(timezone(timedelta(hours=self.utc_offset_hours)))


REGIONS: dict[RegionId, RegionConfig] = {
    RegionId.CALAMBA: RegionConfig(
        id=RegionId.CALAMBA,
        name="Calamba",
        province="Laguna",
        # PLACEHOLDER: approximate city bounds; replace with the OSM admin
        # boundary relation's bbox during the Overpass import.
        bbox=BBox(south=14.13, west=121.03, north=14.27, east=121.23),
        center=LatLng(lat=14.2117, lng=121.1653),
        search_radius_m=15000,  # PLACEHOLDER
        day_start=time(8, 0),
        day_end=time(19, 0),
        outdoor_window_end=time(10, 30),
        # PLACEHOLDER: weekday commute peaks; calibrate per corridor later.
        peak_windows=(
            PeakWindow(start=time(7, 0), end=time(9, 0), factor=1.5),
            PeakWindow(start=time(17, 0), end=time(19, 30), factor=1.6),
        ),
    ),
}


def traffic_factor(region: RegionConfig, depart: time) -> float:
    for w in region.peak_windows:
        if w.start <= depart < w.end:
            return w.factor
    return 1.0
