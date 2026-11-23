"""Load the Sheet exports in data/ into PlaceRecords for an empty database.

Two sources, applied in order:
  1. calamba_osm_places.csv: everything public from OSM, run through the same
     normalize/rules code as a real import, so statuses match.
  2. calamba_curated.csv: hand-researched rows. They win over OSM for name,
     category and outdoor, and Alli's decision sets the status.

Resorts, hot springs and pools are split by walk-in evidence (rules.walk_in).
Walk-in resorts stay places and can be planned. The rest go to `venues` (the
private_venues table) until a partnership exists or a person marks them walk-in.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path

from ..schema import AccessStatus, LatLng, RegionId
from .merge import place_from_osm
from .models import OsmRecord, PlaceRecord, PlaceStatus, PrivateVenue, WalkIn
from .normalize import website, wheelchair
from .rules import RESORT_KINDS, is_resort, walk_in

# Sheet "osm_type" text -> the OSM tag it came from.
TYPE_TAGS: dict[str, tuple[str, str]] = {
    "place of worship": ("amenity", "place_of_worship"), "bakery": ("shop", "bakery"),
    "cafe": ("amenity", "cafe"), "fast food": ("amenity", "fast_food"),
    "restaurant": ("amenity", "restaurant"), "attraction": ("tourism", "attraction"),
    "memorial": ("historic", "memorial"), "monument": ("historic", "monument"),
    "museum": ("tourism", "museum"), "garden": ("leisure", "garden"),
    "nature reserve": ("leisure", "nature_reserve"), "park": ("leisure", "park"),
    "zoo": ("tourism", "zoo"), "guest house": ("tourism", "guest_house"),
    "hotel": ("tourism", "hotel"), "water park": ("leisure", "water_park"),
    "swimming pool": ("leisure", "swimming_pool"),
    "department store": ("shop", "department_store"), "mall": ("shop", "mall"),
    "marketplace": ("amenity", "marketplace"), "cinema": ("amenity", "cinema"),
    "golf course": ("leisure", "golf_course"), "sports centre": ("leisure", "sports_centre"),
}

ALLI_WALK_IN = frozenset({"walk-in", "private"})

# Curated rows are used only when OSM confirmed where they are.
CURATED_MATCHES = {"High", "Confirmed"}
CURATED_SKIP_NOTES = re.compile(r"boat access", re.IGNORECASE)  # not reachable by car
DECISION_STATUS = {"approve": PlaceStatus.FEATURED, "reject": PlaceStatus.HIDDEN}


def _osm_records(path: Path, region: RegionId) -> list[OsmRecord]:
    out = []
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            tag = TYPE_TAGS.get(row["osm_type"])
            if not tag or not row["osm_ref"]:
                continue
            tags = {"name": row["name"], tag[0]: tag[1]}
            if row["wheelchair"] not in ("", "unknown"):
                tags["wheelchair"] = row["wheelchair"]
            if row["opening_hours"] not in ("", "unknown"):
                tags["opening_hours"] = row["opening_hours"]
            if row["website"]:
                tags["website"] = row["website"]
            alli = row.get("alli_walk_in", "").strip().lower()
            if alli in ALLI_WALK_IN:
                tags["alli_walk_in"] = alli  # Alli's call in the Sheet beats every rule
            if "Wikidata" in row["signals"]:
                tags["wikidata"] = "yes"  # the export keeps only the fact, not the id
            if row["local_or_chain"] == "Chain":
                tags["brand"] = row["name"]
            out.append(OsmRecord(
                osm_ref=row["osm_ref"], region=region, name=row["name"], osm_key=tag[0],
                osm_value=tag[1], coords=LatLng(lat=float(row["lat"]), lng=float(row["lng"])), tags=tags,
            ))
    return out


def _apply_curated(places: dict[str, PlaceRecord], path: Path, region: RegionId) -> dict[str, str]:
    """Overlay curated rows. Returns place id -> curated description, used as the stop reason."""
    details: dict[str, str] = {}
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["osm_match"] not in CURATED_MATCHES or row["scope"] != "In Calamba":
                continue
            if CURATED_SKIP_NOTES.search(row["alli_notes"]):
                continue
            pid = f"osm:{row['osm_ref']}"
            status = DECISION_STATUS.get(row["alli_decision"].strip().lower(), PlaceStatus.LISTED)
            fields = dict(
                name=row["name"], category=row["type"], outdoor=row["outdoor"] == "Y",
                status=status, status_reason="curated:sheet",
                overrides={"name": "curated", "category": "curated", "outdoor": "curated", "status": "curated"},
            )
            if row["wheelchair_access"] in ("yes", "limited", "no"):
                fields["wheelchair"] = AccessStatus(row["wheelchair_access"])
            base = places.get(pid)
            if base is None:
                base = PlaceRecord(
                    id=pid, osm_ref=row["osm_ref"], region=region, name=row["name"], category=row["type"],
                    kind="curated", coords=LatLng(lat=float(row["lat"]), lng=float(row["lng"])),
                )
            places[pid] = PlaceRecord.model_validate({**base.model_dump(), **fields})
            details[pid] = row["details"]
    return details


def _boat_only(path: Path) -> set[str]:
    with path.open(newline="", encoding="utf-8") as f:
        return {f"osm:{r['osm_ref']}" for r in csv.DictReader(f)
                if r["osm_ref"] and CURATED_SKIP_NOTES.search(r["alli_notes"])}


@dataclass
class Seed:
    places: list[PlaceRecord]
    details: dict[str, str]  # place id -> curated description
    venues: list[PrivateVenue] = field(default_factory=list)


def _venue_from_osm(rec: OsmRecord, verdict: WalkIn, reason: str) -> PrivateVenue:
    return PrivateVenue(
        id=f"osm:{rec.osm_ref}", osm_ref=rec.osm_ref, region=rec.region, name=rec.name,
        kind=rec.osm_value, coords=rec.coords, wheelchair=wheelchair(rec.tags),
        opening_hours=rec.tags.get("opening_hours"), website=website(rec.tags),
        walk_in=verdict, walk_in_reason=reason,
    )


def _venue_from_place(p: PlaceRecord, details: str | None, verdict: WalkIn, reason: str) -> PrivateVenue:
    return PrivateVenue(
        id=p.id, osm_ref=p.osm_ref, region=p.region, name=p.name, kind=p.kind, coords=p.coords,
        wheelchair=p.wheelchair, opening_hours=p.opening_hours, website=p.website, details=details,
        walk_in=verdict, walk_in_reason=reason,
    )


def load_seed(seed_dir: Path, region: RegionId = RegionId.CALAMBA) -> Seed:
    places: dict[str, PlaceRecord] = {}
    resorts: dict[str, OsmRecord] = {}
    for rec in _osm_records(seed_dir / "calamba_osm_places.csv", region):
        if rec.osm_value in RESORT_KINDS:
            resorts[f"osm:{rec.osm_ref}"] = rec
        p = place_from_osm(rec)
        if p is not None:
            places[p.id] = p
    details = _apply_curated(places, seed_dir / "calamba_curated.csv", region)

    # Resorts: walk-ins stay places, the rest move to private venues.
    venues: dict[str, PrivateVenue] = {}
    for pid, p in list(places.items()):
        if not is_resort(p.kind, p.category):
            continue
        rec = resorts.get(pid)
        verdict, reason = walk_in(p.name, rec.tags if rec else {}, curated=p.status_reason == "curated:sheet")
        if verdict is not WalkIn.YES:
            venues[pid] = _venue_from_place(p, details.pop(pid, None), verdict, reason)
            del places[pid]
    # Pools are not imported as places. A walk-in pool resort is added as a water park.
    for pid, rec in resorts.items():
        if pid in places or pid in venues:
            continue
        verdict, reason = walk_in(rec.name, rec.tags, curated=False)
        as_park = rec.model_copy(update={"osm_value": "water_park", "tags": {**rec.tags, "leisure": "water_park"}})
        p = place_from_osm(as_park) if verdict is WalkIn.YES else None
        if p is not None:
            places[pid] = p
        else:
            venues[pid] = _venue_from_osm(rec, verdict, reason)
    # Beta is car travel only, so a walk-in resort reached by boat is not planned yet.
    for pid in _boat_only(seed_dir / "calamba_curated.csv") & places.keys():
        venues[pid] = _venue_from_place(places.pop(pid), details.pop(pid, None), WalkIn.YES, "rule:boat_access_only")
    return Seed(list(places.values()), details, list(venues.values()))
