"""Apply a fresh OSM import to existing places without losing human edits."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..schema import AccessStatus
from . import normalize, rules
from .models import OSM_OWNED_FIELDS, OsmRecord, PlaceRecord


@dataclass
class MergeResult:
    upserts: list[PlaceRecord] = field(default_factory=list)
    added: int = 0
    updated: int = 0
    missing: list[str] = field(default_factory=list)  # place ids flagged possibly_closed


def place_from_osm(rec: OsmRecord) -> PlaceRecord | None:
    """Build a brand-new place from an OSM record (first time we see it)."""
    cls = normalize.classify(rec.tags)
    if cls is None:
        return None
    _, kind, category, outdoor = cls
    chain = rules.is_chain(rec.name, rec.tags)
    status, reason = rules.resolve_status(rec.name, kind, rec.tags, chain, {}, None)
    return PlaceRecord(
        id=f"osm:{rec.osm_ref}", osm_ref=rec.osm_ref, region=rec.region,
        name=rec.name, category=category, kind=kind, coords=rec.coords,
        outdoor=outdoor, is_chain=chain, status=status, status_reason=reason,
        wheelchair=normalize.wheelchair(rec.tags),
        opening_hours=rec.tags.get("opening_hours"),
        website=normalize.website(rec.tags),
    )


def refresh(existing: PlaceRecord, rec: OsmRecord) -> PlaceRecord:
    """Update OSM-owned fields, skipping any field a person has overridden."""
    fresh = place_from_osm(rec)
    if fresh is None:  # OSM tags changed so it no longer qualifies
        return existing.model_copy(update={"possibly_closed": True})
    changes = {
        f: getattr(fresh, f) for f in OSM_OWNED_FIELDS
        if f not in existing.overrides and getattr(fresh, f) != getattr(existing, f)
    }
    # OSM saying "unknown" never erases a known accessibility value from an owner.
    if changes.get("wheelchair") is AccessStatus.UNKNOWN:
        changes.pop("wheelchair")
    status, reason = rules.resolve_status(
        changes.get("name", existing.name), changes.get("kind", existing.kind),
        rec.tags, changes.get("is_chain", existing.is_chain),
        existing.overrides, existing.status,
    )
    changes.update(status=status, status_reason=reason, possibly_closed=False)
    return existing.model_copy(update=changes)


def merge_run(existing: dict[str, PlaceRecord], incoming: list[OsmRecord]) -> MergeResult:
    """existing is keyed by osm_ref. Pure: the caller writes the result to the DB."""
    out = MergeResult()
    seen: set[str] = set()
    for rec in incoming:
        seen.add(rec.osm_ref)
        old = existing.get(rec.osm_ref)
        if old is None:
            new = place_from_osm(rec)
            if new is not None:
                out.upserts.append(new)
                out.added += 1
            continue
        new = refresh(old, rec)
        if new != old:
            out.upserts.append(new)
            out.updated += 1
    for ref, old in existing.items():
        if ref not in seen and not old.possibly_closed:
            out.upserts.append(old.model_copy(update={"possibly_closed": True}))
            out.missing.append(old.id)
    return out
