"""Short, plain reasons shown under each stop. No LLM in beta: template text only."""

from __future__ import annotations

from ..places.models import PlaceRecord
from ..schema import Interest
from .catalog import Role

MAX = 280


def reason_for(p: PlaceRecord, role: Role, details: dict[str, str], *, morning: bool = False,
               meal: str = "", prev_name: str | None = None) -> str:
    if role is Role.MEAL:
        where = f"near {prev_name}" if prev_name else "on the way"
        text = f"{meal.capitalize() or 'A meal'} {where}."
        if not p.is_chain:
            text += " A local place, not a chain."
        if p.id in details:
            text += f" {details[p.id]}."
        return _clip(text)
    if role is Role.CAFE:
        return _clip("Coffee and a sit-down break in the afternoon.")
    if p.id in details:
        text = details[p.id].rstrip(".") + "."
        if morning and p.outdoor and p.category != Interest.HOT_SPRINGS:
            text += " Outdoors, so it goes early while it is still cool."
        return _clip(text)
    return _clip({
        "landmark": "A local landmark close to your other stops today.",
        Interest.PARKS: "Open-air stop" + (", early while it is still cool." if morning else "."),
        Interest.HOT_SPRINGS: "Warm pools for a long, slow stretch of the day.",
        Interest.MALLS: "Indoors and air-conditioned, for a break from the heat.",
    }.get(p.category, "Close to your other stops today."))


def _clip(s: str) -> str:
    return s if len(s) <= MAX else s[: MAX - 1].rstrip() + "…"
