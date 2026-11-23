"""Import places for one region from an OSM .pbf file (Geofabrik Philippines extract).

Usage (on a machine with the file downloaded):

    # 1. once a month: download the extract (about 500 MB)
    #    https://download.geofabrik.de/asia/philippines-latest.osm.pbf
    # 2. optional but faster: crop to the region first with the osmium CLI
    #    osmium extract -b 121.03,14.13,121.23,14.27 philippines-latest.osm.pbf -o calamba.osm.pbf
    # 3. run
    python -m app.places.osm_import calamba.osm.pbf --region calamba --out calamba.jsonl

Output is one OsmRecord per line (JSONL). Writing to Postgres is a separate step
(merge.merge_run decides what changes), so this script never touches the database.

Needs `pip install osmium` (pyosmium 4.x). Only this file depends on it.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable, Iterator
from pathlib import Path

from ..regions import REGIONS
from ..schema import LatLng, RegionId
from .models import OsmRecord
from .normalize import IMPORT_KEYS, classify

# A raw feature before validation: (osm_ref, tags, lat, lng)
RawFeature = tuple[str, dict[str, str], float, float]


def records_from_features(features: Iterable[RawFeature], region: RegionId) -> Iterator[OsmRecord]:
    """Keep named, supported features inside the region's bbox. Pure; easy to test."""
    bbox = REGIONS[region].bbox
    seen: set[str] = set()
    for ref, tags, lat, lng in features:
        if ref in seen:
            continue
        point = LatLng(lat=lat, lng=lng)
        if not bbox.contains(point):
            continue
        cls = classify(tags)
        if cls is None:
            continue
        key, value, _, _ = cls
        seen.add(ref)
        yield OsmRecord(osm_ref=ref, region=region, name=tags["name"].strip()[:200],
                        osm_key=key, osm_value=value, coords=point, tags=tags)


def read_pbf(path: Path) -> Iterator[RawFeature]:
    """Nodes use their own location; closed ways and multipolygons use the
    average of their outer-ring points (good enough for routing to a venue)."""
    import osmium  # imported here so the rest of the package works without it

    fp = (osmium.FileProcessor(str(path))
          .with_filter(osmium.filter.KeyFilter(*IMPORT_KEYS))
          .with_locations()
          .with_areas())
    for obj in fp:
        tags = {t.k: t.v for t in obj.tags}
        if obj.is_node():
            if obj.location.valid():
                yield f"node/{obj.id}", tags, obj.location.lat, obj.location.lon
        elif obj.is_area():
            pts = [(n.lat, n.lon) for ring in obj.outer_rings() for n in ring if n.location.valid()]
            if pts:
                kind = "way" if obj.from_way() else "relation"
                lat = sum(p[0] for p in pts) / len(pts)
                lng = sum(p[1] for p in pts) / len(pts)
                yield f"{kind}/{obj.orig_id()}", tags, lat, lng


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("pbf", type=Path)
    ap.add_argument("--region", type=RegionId, default=RegionId.CALAMBA)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)

    count = 0
    with args.out.open("w", encoding="utf-8") as f:
        for rec in records_from_features(read_pbf(args.pbf), args.region):
            f.write(json.dumps(rec.model_dump(mode="json"), ensure_ascii=False) + "\n")
            count += 1
    print(f"{count} places written to {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
