"""Choose what goes into each day: one area per day, sights first, meals around them.

Choices use straight-line estimates (fast, no network). Real drive times are
applied afterwards in timeline.build_day.
"""

from __future__ import annotations

from datetime import time

from ..places.models import PlaceRecord
from ..regions import RegionConfig
from ..routing import EstimateRouter
from ..schema import MAX_STOPS_PER_DAY, AccessNeed, Interest, LatLng, TripIntake
from .catalog import Catalog, Role, access_ok, dwell_for
from .reasons import reason_for
from .scoring import km, meal_score, sight_allowed, sight_score
from .timeline import Visit

AREA_KM = 3.0          # a day stays inside this distance of its first sight
WIDER_AREA_KM = 6.0    # used only when the area runs out
MEAL_MAX_KM = 5.0
MEAL_DETOUR_PENALTY = 1.5  # score points per extra km driven to reach a meal
MEAL_DRIVE_MIN = 10       # rough allowance while choosing sights; real times come later
SIGHTS_END = 17 * 60 + 30
LUNCH_AT = 11 * 60 + 30
DINNER_AT = 18 * 60
AFTERNOON_AT = 13 * 60  # with no meal stops, the second half of the day starts here
LIMIT_PER_DAY = {Interest.HOT_SPRINGS: 1, Interest.MALLS: 1}

_est = EstimateRouter()


def _drive_min(a: LatLng, b: LatLng) -> int:
    return round(_est.drive(a, b).duration_s / 60)


def _hhmm(minutes: int) -> time:
    return time(minutes // 60, minutes % 60)


class DayBuilder:
    def __init__(self, intake: TripIntake, region: RegionConfig, catalog: Catalog,
                 stay: LatLng, used: set[str]):
        self.intake, self.region, self.catalog, self.stay, self.used = intake, region, catalog, stay, used
        wheelchair = AccessNeed.WHEELCHAIR in intake.access_needs
        radius_km = region.search_radius_m / 1000

        def ok(p: PlaceRecord) -> bool:
            return access_ok(p, wheelchair, intake.allow_unverified_access) and km(stay, p.coords) <= radius_km

        self.sights = [p for p in catalog.with_role(Role.SIGHT) if ok(p) and sight_allowed(p, intake)]
        self.meals = [p for p in catalog.with_role(Role.MEAL) if ok(p)]
        self.cafes = [p for p in catalog.with_role(Role.CAFE) if ok(p)]
        # Room left in a day after lunch, dinner (unless they bring food) and a coffee stop if wanted.
        meals = 2 if intake.include_meals else 0
        room = MAX_STOPS_PER_DAY - meals - (1 if Interest.CAFES in intake.interests else 0)
        self.max_sights = min(room, intake.places_per_day or room)

    # -------------------------------------------------------------- helpers
    def _take_eatery(self, pool: list[PlaceRecord], pos: LatLng, nxt: LatLng, label: str, prev: str | None,
                     clock: int, not_before: int | None) -> tuple[Visit, int, LatLng] | None:
        """Best place to eat between `pos` and the next stop `nxt`, judged by the detour it adds."""
        options = [p for p in pool if p.id not in self.used and km(pos, p.coords) <= MEAL_MAX_KM]
        if not options:
            return None

        def detour(p: PlaceRecord) -> float:
            return km(pos, p.coords) + km(p.coords, nxt) - km(pos, nxt)

        best = max(options, key=lambda p: meal_score(p, self.intake) - MEAL_DETOUR_PENALTY * detour(p))
        role = Role.MEAL if pool is self.meals else Role.CAFE
        self.used.add(best.id)
        arrive = clock + _drive_min(pos, best.coords)
        if not_before is not None:
            arrive = max(arrive, not_before)
        dwell = dwell_for(best, role)
        visit = Visit(best, dwell, reason_for(best, role, self.catalog.details, meal=label, prev_name=prev),
                      _hhmm(not_before) if not_before is not None else None)
        return visit, arrive + dwell, best.coords

    def _sight_value(self, p: PlaceRecord, pos: LatLng, clock: int) -> float:
        v = sight_score(p, self.intake) - 0.3 * km(pos, p.coords)
        if p.outdoor and p.category != Interest.HOT_SPRINGS:
            if clock < self.region.outdoor_window_end.hour * 60 + self.region.outdoor_window_end.minute:
                v += 1.5   # outdoors while it is cool
            elif clock < 15 * 60 + 30:
                v -= 1.0   # midday heat
            else:
                v += 1.0   # late afternoon, sunset spots
        return v

    # -------------------------------------------------------------- one day
    def build(self) -> list[Visit]:
        picks = self._choose_sights()
        if not picks:
            return []
        return self._with_meals(shortest_loop(self.stay, picks))

    def _choose_sights(self) -> list[PlaceRecord]:
        """Which sights fit today. Order here is only a guess; shortest_loop fixes it."""
        free = [p for p in self.sights if p.id not in self.used]
        if not free:
            return []
        seed = max(free, key=lambda p: sight_score(p, self.intake) - 0.15 * km(self.stay, p.coords))
        clock = self.region.day_start.hour * 60 + self.region.day_start.minute
        pos = self.stay
        picks: list[PlaceRecord] = []
        counts: dict[str, int] = {}
        lunch_counted = False
        while len(picks) < self.max_sights:
            if self.intake.include_meals and not lunch_counted and clock >= LUNCH_AT:
                clock, lunch_counted = clock + 60 + MEAL_DRIVE_MIN, True
            pick = self._next_sight(seed.coords, pos, clock, counts, first=not picks)
            if pick is None:
                break
            picks.append(pick)
            self.used.add(pick.id)
            counts[pick.category] = counts.get(pick.category, 0) + 1
            clock += _drive_min(pos, pick.coords) + dwell_for(pick, Role.SIGHT)
            pos = pick.coords
        return picks

    def _with_meals(self, order: list[PlaceRecord]) -> list[Visit]:
        """Walk the day in order and slot lunch, coffee and dinner in at the right times."""
        cool_until = self.region.outdoor_window_end.hour * 60 + self.region.outdoor_window_end.minute
        clock = self.region.day_start.hour * 60 + self.region.day_start.minute
        pos, prev_name = self.stay, None
        visits: list[Visit] = []
        lunch_done = False

        def eat(pool: list[PlaceRecord], label: str, not_before: int | None, nxt: LatLng) -> None:
            nonlocal clock, pos, prev_name
            got = self._take_eatery(pool, pos, nxt, label, prev_name, clock, not_before)
            if got:
                visits.append(got[0])
                clock, pos, prev_name = got[1], got[2], got[0].place.name

        meals = self.intake.include_meals
        # Spread the places over the day: about half before lunch, the rest after,
        # so a short list doesn't fill the morning and leave the afternoon empty.
        morning_count = (len(order) + 1) // 2
        for n, p in enumerate(order):
            if not lunch_done and (clock >= LUNCH_AT or n == morning_count):
                if meals:
                    eat(self.meals, "lunch", LUNCH_AT, p.coords)
                elif clock < AFTERNOON_AT:  # they bring food: leave time for it, then carry on
                    clock = AFTERNOON_AT
                lunch_done = True
            arrive = clock + _drive_min(pos, p.coords)
            reason = reason_for(p, Role.SIGHT, self.catalog.details, morning=arrive < cool_until)
            starts_afternoon = not meals and lunch_done and n == morning_count
            visits.append(Visit(p, dwell_for(p, Role.SIGHT), reason,
                                _hhmm(AFTERNOON_AT) if starts_afternoon else None))
            clock, pos, prev_name = arrive + dwell_for(p, Role.SIGHT), p.coords, p.name
        if meals and not lunch_done:
            eat(self.meals, "lunch", LUNCH_AT, self.stay)
        if Interest.CAFES in self.intake.interests and clock < 16 * 60:
            eat(self.cafes, "coffee", None, self.stay)
        if meals:
            eat(self.meals, "dinner", DINNER_AT, self.stay)
        return visits

    def _next_sight(self, center: LatLng, pos: LatLng, clock: int, counts: dict[str, int],
                    first: bool) -> PlaceRecord | None:
        for radius in (AREA_KM, WIDER_AREA_KM):
            options = [
                p for p in self.sights
                if p.id not in self.used
                and km(center, p.coords) <= radius
                and counts.get(p.category, 0) < LIMIT_PER_DAY.get(p.category, 99)
                and clock + _drive_min(pos, p.coords) + dwell_for(p, Role.SIGHT) <= SIGHTS_END
            ]
            if options:
                if first:  # the day's anchor is the best sight, not the closest
                    return max(options, key=lambda p: sight_score(p, self.intake) - 0.15 * km(self.stay, p.coords))
                return max(options, key=lambda p: self._sight_value(p, pos, clock))
        return None


def _loop_km(stay: LatLng, order: list[PlaceRecord]) -> float:
    pts = [stay, *(p.coords for p in order), stay]
    return sum(km(a, b) for a, b in zip(pts, pts[1:]))


def shortest_loop(stay: LatLng, picks: list[PlaceRecord]) -> list[PlaceRecord]:
    """Order a day's sights to keep driving short: nearest-neighbour, then 2-opt.

    A day has at most a handful of sights, so this is exact enough and instant.
    Of the two directions round the loop, the one that reaches outdoor places
    (not pools) sooner is kept, so they land in the cool morning.
    """
    left, pos, order = list(picks), stay, []
    while left:
        nxt = min(left, key=lambda p: km(pos, p.coords))
        order.append(nxt)
        left.remove(nxt)
        pos = nxt.coords
    improved = True
    while improved:
        improved = False
        for i in range(len(order) - 1):
            for j in range(i + 1, len(order)):
                cand = order[:i] + order[i:j + 1][::-1] + order[j + 1:]
                if _loop_km(stay, cand) < _loop_km(stay, order) - 1e-9:
                    order, improved = cand, True

    def outdoor_rank(o: list[PlaceRecord]) -> int:
        return sum(i for i, p in enumerate(o) if p.outdoor and p.category != Interest.HOT_SPRINGS)

    return min(order, order[::-1], key=outdoor_rank)
