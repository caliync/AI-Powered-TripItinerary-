"""Automatic status rules, so a person only reviews the places that matter.

Order of precedence:
  1. A status set by a person (overrides["status"]) always wins.
  2. HIDE rules  -> hidden   (private, generic names, sub-pools of a resort)
  3. REVIEW rules -> pending (could be featured; a person decides)
  4. everything else that was imported -> listed
Chains can be listed but never featured.
"""

from __future__ import annotations

import re

from .models import PlaceStatus, WalkIn

# Brands seen in Calamba OSM data (2026-11-18). Extend as new ones appear.
CHAIN_NAMES = frozenset({
    "jollibee", "mcdonald's", "chowking", "mang inasal", "kfc", "greenwich",
    "starbucks", "red ribbon", "goldilocks", "shakey's", "max's restaurant",
    "bonchon chicken", "army navy burger + burrito", "potato corner", "pizza hut",
    "dunkin'", "yellow cab pizza", "yellow cab pizza co.", "angel's burger",
    "angels burger", "angel's pizza", "minute burger", "burger king", "burger machine",
    "the coffee bean & tea leaf", "seattle's best coffee", "pancake house",
    "the pancake house", "kenny rogers roasters", "andok's", "baliwag",
    "krispy kreme", "julie's", "chooks to go", "chatime", "domino's", "domino's pizza",
    "café amazon", "mary grace", "infinitea", "david's tea house", "siomai king",
    "siomai house", "the shawarma shack", "zagu", "turks", "teds lapaz batchoy",
    "the old spaghetti house", "puregold", "puregold jr", "puregold jr.",
    "puregold extra", "robinsons supermarket", "robinson's easymart", "sm supermarket",
    "the sm store", "sm city calamba", "waltermart", "shopwise", "citymall calamba",
    "lianas discount city", "merrymart grocery", "o!save", "dali everyday grocery",
})

# Resorts, hot springs and pools. Alli 2026-11-18: a resort that takes walk-in
# (day-tour) guests is a public place and can be planned. One that is rented
# out whole or needs booking stays in the private_venues table until there is
# a partnership. OSM can't say which is which, so we look for evidence.
RESORT_KINDS = frozenset({"water_park", "resort", "swimming_pool"})
RESORT_CATEGORIES = frozenset({"hot_springs"})
_PRIVATE_NAME = re.compile(r"\bprivate\b|\bprivate pool\b", re.IGNORECASE)


def is_resort(kind: str, category: str) -> bool:
    return kind in RESORT_KINDS or str(category) in RESORT_CATEGORIES


def walk_in(name: str, tags: dict[str, str], curated: bool) -> tuple[WalkIn, str]:
    """Whether a resort takes walk-in guests, and the rule that decided it."""
    alli = tags.get("alli_walk_in")
    if alli == "walk-in":
        return WalkIn.YES, "alli:sheet"
    if alli == "private":
        return WalkIn.NO, "alli:sheet"
    if curated:
        return WalkIn.YES, "curated:sheet"  # on Alli's own Places list
    if _PRIVATE_NAME.search(name):
        return WalkIn.NO, "rule:private_name"
    if tags.get("access", "").lower() in _PRIVATE_ACCESS:
        return WalkIn.NO, "rule:private_access"
    if tags.get("opening_hours", "").strip() == "24/7":
        return WalkIn.NO, "rule:rented_by_the_day"  # whole-place rentals list 24/7
    if tags.get("website") or tags.get("wikidata"):
        return WalkIn.YES, "rule:public_listing"
    if tags.get("opening_hours"):
        return WalkIn.YES, "rule:day_hours"  # swim hours mean the gate is open to the public
    return WalkIn.UNKNOWN, "rule:no_walk_in_evidence"


# Kinds worth a person's eye: they could become featured.
REVIEW_KINDS = frozenset({
    "museum", "attraction", "viewpoint", "monument", "memorial", "zoo",
    "nature_reserve", "park", "waterfall", "hot_spring", "farm", "farmland",
})

_GENERIC_NAME = re.compile(
    r"^(pool\s*#?\d*|swimming pool|clubhouse|club house|courtyard|canteen|playground|park)$",
    re.IGNORECASE,
)
_PRIVATE_ACCESS = frozenset({"private", "no", "customers_only_members"})


def is_chain(name: str, tags: dict[str, str]) -> bool:
    if tags.get("brand") or tags.get("brand:wikidata"):
        return True
    return name.strip().lower() in CHAIN_NAMES


def auto_status(name: str, kind: str, tags: dict[str, str]) -> tuple[PlaceStatus, str]:
    """Status and the rule that chose it (stored in places.status_reason)."""
    if tags.get("access", "").lower() in _PRIVATE_ACCESS:
        return PlaceStatus.HIDDEN, "rule:private_access"
    if _GENERIC_NAME.match(name.strip()):
        return PlaceStatus.HIDDEN, "rule:generic_name"
    if kind in REVIEW_KINDS:
        return PlaceStatus.PENDING, "rule:review_kind"
    return PlaceStatus.LISTED, "rule:default_listed"


def resolve_status(
    name: str, kind: str, tags: dict[str, str], chain: bool,
    overrides: dict[str, str], current: PlaceStatus | None,
) -> tuple[PlaceStatus, str]:
    """Final status for an import run. A person's choice is never undone."""
    if "status" in overrides and current is not None:
        if chain and current is PlaceStatus.FEATURED:
            return PlaceStatus.LISTED, "rule:chain_not_featured"
        return current, overrides["status"]
    status, reason = auto_status(name, kind, tags)
    return status, reason


def check_featured_allowed(chain: bool) -> None:
    """Called by the review screen before saving 'featured'."""
    if chain:
        raise ValueError("chains can be listed but not featured")
