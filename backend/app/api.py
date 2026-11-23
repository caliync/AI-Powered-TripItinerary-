"""HTTP API for the website. Run with: uvicorn app.api:app --reload

Every route lives under /api/v1. Errors use one shape:
    {"detail": {"code": "<machine code>", "message": "<sentence for the traveller>"}}
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .config import Settings, get_settings
from .db import StaleVersion, Store
from .geocode import StayNotFound, StayOutsideRegion, locate_stay, suggest_stays
from .places.matching import best_match
from .places.models import PlaceRecord, PrivateVenue, Submission
from .places.seed import load_seed
from .planner import build_itinerary, region_for
from .planner.catalog import Catalog
from .planner.swap import (
    SwapError,
    apply_add,
    apply_remove,
    apply_swap,
    day_choices,
    day_recommendations,
    swap_options,
)
from .regions import REGIONS
from .routing import EstimateRouter, OsrmRouter, Router
from .schema import (
    Itinerary,
    RegionId,
    StaySuggestion,
    StopAdd,
    StopChoices,
    StopRemove,
    SwapApply,
    SwapCandidate,
    SwapRequest,
    TripIntake,
)


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorBody(BaseModel):
    detail: ErrorDetail


class SubmissionReceived(BaseModel):
    status: Literal["pending"] = "pending"


def fail(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code, detail={"code": code, "message": message})


@dataclass
class AppState:
    settings: Settings
    store: Store
    http: httpx.Client
    # Public places plus private venues: used to find the stay and to match owner submissions.
    all_places: dict[RegionId, list[PlaceRecord | PrivateVenue]]
    catalogs: dict[RegionId, Catalog]

    def router(self) -> Router:
        if self.settings.osrm_url:
            return OsrmRouter(self.settings.osrm_url, self.http)
        return EstimateRouter()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        store = Store(settings.db_path)
        if store.place_count() == 0:
            seed = load_seed(settings.seed_dir)
            store.upsert_places(seed.places, seed.details)
            store.upsert_venues(seed.venues)
        elif not any(store.venues(r) for r in REGIONS):
            # A database made before private venues were split out: move them over.
            seed = load_seed(settings.seed_dir)
            store.upsert_venues(seed.venues)
            store.remove_places([v.id for v in seed.venues])
        http = httpx.Client(timeout=settings.http_timeout_s, headers={"User-Agent": settings.user_agent})
        loaded = {r: store.places(r) for r in REGIONS}
        app.state.ctx = AppState(
            settings=settings, store=store, http=http,
            all_places={r: [*p, *store.venues(r)] for r, (p, _) in loaded.items()},
            catalogs={r: Catalog.build(p, d) for r, (p, d) in loaded.items()},
        )
        yield
        http.close()

    app = FastAPI(title="Calamba Trip Planner API", version="0.1.0", lifespan=lifespan,
                  responses={422: {"model": ErrorBody}})
    app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins),
                       allow_methods=["GET", "POST"], allow_headers=["Content-Type"])
    app.include_router(api)

    @app.exception_handler(RequestValidationError)
    async def invalid_input(_: Request, exc: RequestValidationError) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        where = ".".join(str(p) for p in first.get("loc", ())[1:])
        message = str(first.get("msg", "Invalid input")).removeprefix("Value error, ")
        return JSONResponse(status_code=422, content={"detail": {
            "code": "invalid_input", "message": f"{where}: {message}" if where else message}})

    return app


def ctx(request: Request) -> AppState:
    return request.app.state.ctx


api = APIRouter(prefix="/api/v1")
STALE = "This plan changed in another tab. Reload to see the latest."
ERRORS = {404: {"model": ErrorBody}, 409: {"model": ErrorBody}}


@api.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@api.get("/stays/suggest", response_model=list[StaySuggestion])
def stays_suggest(q: str = Query(max_length=100), region: RegionId = RegionId.CALAMBA,
                  c: AppState = Depends(ctx)) -> list[StaySuggestion]:
    """Hotels, guest houses and resorts that fit what the traveller has typed so far."""
    return [StaySuggestion(name=p.name, kind=p.kind, coords=p.coords)
            for p in suggest_stays(q, c.all_places[region])]


@api.post("/itinerary/generate", response_model=Itinerary, status_code=status.HTTP_201_CREATED)
def generate(intake: TripIntake, c: AppState = Depends(ctx)) -> Itinerary:
    region = REGIONS[intake.region]
    try:
        stay = locate_stay(intake.stay, region, c.all_places[intake.region], c.settings.nominatim_url, c.http)
    except StayNotFound:
        raise fail(422, "stay_not_found", f"We couldn't find \"{intake.stay.label}\" in {region.name}. "
                   "Try the full name of the hotel or a street address.") from None
    except StayOutsideRegion:
        raise fail(422, "stay_outside_region", f"\"{intake.stay.label}\" is outside {region.name}. "
                   f"The beta only plans trips from a stay in {region.name}.") from None
    it = build_itinerary(intake, stay, c.catalogs[intake.region], c.router(), region)
    c.store.save_itinerary(it)
    return it


def _load(c: AppState, itinerary_id: UUID) -> Itinerary:
    it = c.store.get_itinerary(itinerary_id)
    if it is None:
        raise fail(404, "not_found", "This plan doesn't exist.")
    return it


@api.get("/itinerary/{itinerary_id}", response_model=Itinerary, responses=ERRORS)
def get_itinerary(itinerary_id: UUID, c: AppState = Depends(ctx)) -> Itinerary:
    return _load(c, itinerary_id)


@api.post("/itinerary/{itinerary_id}/swap", response_model=list[SwapCandidate], responses=ERRORS)
def swap(itinerary_id: UUID, req: SwapRequest, c: AppState = Depends(ctx)) -> list[SwapCandidate]:
    it = _load(c, itinerary_id)
    if req.version != it.version:
        raise fail(409, "stale_version", STALE)
    try:
        return swap_options(it, req, c.catalogs[it.intake.region])
    except SwapError as e:
        raise fail(422, "bad_swap", str(e)) from None


@api.get("/itinerary/{itinerary_id}/days/{day_index}/choices", response_model=list[StopChoices],
         responses=ERRORS)
def choices(itinerary_id: UUID, day_index: int, c: AppState = Depends(ctx)) -> list[StopChoices]:
    """Suggestions to pick from for each stop (Morning, Afternoon, Evening) of one day."""
    it = _load(c, itinerary_id)
    try:
        return day_choices(it, day_index, c.catalogs[it.intake.region])
    except SwapError as e:
        raise fail(404, "not_found", str(e)) from None


@api.post("/itinerary/{itinerary_id}/swap/apply", response_model=Itinerary, responses=ERRORS)
def swap_apply(itinerary_id: UUID, req: SwapApply, c: AppState = Depends(ctx)) -> Itinerary:
    it = _load(c, itinerary_id)
    if req.version != it.version:
        raise fail(409, "stale_version", STALE)
    region = region_for(it.intake, REGIONS[it.intake.region])
    try:
        updated = apply_swap(it, req, c.catalogs[it.intake.region], c.router(), region)
    except SwapError as e:
        raise fail(422, "bad_swap", str(e)) from None
    try:
        c.store.replace_itinerary(updated, expected_version=req.version)
    except StaleVersion:
        raise fail(409, "stale_version", STALE) from None
    return updated


@api.get("/itinerary/{itinerary_id}/days/{day_index}/recommendations", response_model=list[SwapCandidate],
         responses=ERRORS)
def recommendations(itinerary_id: UUID, day_index: int, c: AppState = Depends(ctx)) -> list[SwapCandidate]:
    """Places near this day's route that the traveller can add to the morning, afternoon or evening."""
    it = _load(c, itinerary_id)
    try:
        return day_recommendations(it, day_index, c.catalogs[it.intake.region])
    except SwapError as e:
        raise fail(404, "not_found", str(e)) from None


def _save_edit(c: AppState, it: Itinerary, build) -> Itinerary:
    region = region_for(it.intake, REGIONS[it.intake.region])
    try:
        updated = build(it, c.catalogs[it.intake.region], c.router(), region)
    except SwapError as e:
        raise fail(422, "bad_swap", str(e)) from None
    try:
        c.store.replace_itinerary(updated, expected_version=it.version)
    except StaleVersion:
        raise fail(409, "stale_version", STALE) from None
    return updated


@api.post("/itinerary/{itinerary_id}/stops/add", response_model=Itinerary, responses=ERRORS)
def stop_add(itinerary_id: UUID, req: StopAdd, c: AppState = Depends(ctx)) -> Itinerary:
    it = _load(c, itinerary_id)
    if req.version != it.version:
        raise fail(409, "stale_version", STALE)
    return _save_edit(c, it, lambda i, cat, router, region: apply_add(i, req, cat, router, region))


@api.post("/itinerary/{itinerary_id}/stops/remove", response_model=Itinerary, responses=ERRORS)
def stop_remove(itinerary_id: UUID, req: StopRemove, c: AppState = Depends(ctx)) -> Itinerary:
    it = _load(c, itinerary_id)
    if req.version != it.version:
        raise fail(409, "stale_version", STALE)
    return _save_edit(c, it, lambda i, cat, router, region: apply_remove(i, req, cat, router, region))


@api.post("/places/submissions", response_model=SubmissionReceived, status_code=status.HTTP_202_ACCEPTED)
def submit_business(sub: Submission, c: AppState = Depends(ctx)) -> SubmissionReceived:
    """Stored for a person to review. Nothing appears in plans until then."""
    region = REGIONS[sub.region]
    if not region.bbox.contains(sub.coords):
        raise fail(422, "outside_region",
                   f"That pin is outside {region.name}. The beta only lists places in {region.name}.")
    match = best_match(sub, c.all_places[sub.region])
    c.store.add_submission(sub, match[0].id if match else None, match[1] if match else None)
    return SubmissionReceived()


app = create_app()
