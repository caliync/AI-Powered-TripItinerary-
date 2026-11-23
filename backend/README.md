# Calamba Trip Planner, backend

This is the FastAPI and Pydantic backend for the beta. It covers Calamba only, plans car trips, and uses OpenStreetMap places only.

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
uvicorn app.api:app --reload                        # http://localhost:8000/docs
pytest -q
```

On the first start, `data/app.db` is created and filled from the CSV copies of the project Sheet in `data/`. See [data/README.md](data/README.md).

The website uses this API by default: start it here, then run `npm run dev` in `frontend/`, which proxies `/api` to port 8000. Use `npm run dev:mock` there to work on the website without the API.

## How a plan is made

1. **Find the stay.** The planner uses coordinates the website sends, then hotels already in the database, then Nominatim inside Calamba.
2. **Choose each day's places** (`app/planner/days.py`).
   - Each day centres on its best unused sight and stays within about 3 km of it, widening to 6 km if the area runs out.
   - Outdoor places get a boost before 10:30 and around sunset.
   - Lunch is from 11:30 and dinner from 18:00. Local places are preferred over chains.
   - A day has at most 8 stops, one hot spring and one mall.
   - Only walk-in places are planned. Resorts that take walk-in guests are public places. Private or unconfirmed resorts live in the `private_venues` table, are never planned or offered as swaps, and are only used to find where the traveller is staying.
3. **Time the day** (`app/planner/timeline.py`).
   - Drive times come from OSRM, multiplied by the rush-hour factors in `app/regions.py`.
   - If OSRM doesn't answer, the planner uses a straight-line estimate and every day says so.
4. **Add warnings.** These cover unconfirmed wheelchair access, rush-hour drives, light days and estimated drive times.

Swaps (`app/planner/swap.py`) offer up to 5 places with the same role within 3 km, widening to 5 km if none are found. A version check stops two tabs from overwriting each other.

## Shared types

`app/schema.py` is the only definition of the trip types. After changing it, run `../scripts/check-types.sh` and commit the regenerated `frontend/types/openapi.json` and `api.gen.ts`. CI fails if you forget.

## Settings (environment variables)

| Name | Default | Purpose |
| --- | --- | --- |
| `DB_PATH` | `data/app.db` | SQLite file |
| `OSRM_URL` | public OSRM demo server | Set it empty to always use estimates. Self-host before launch. |
| `NOMINATIM_URL` | public Nominatim | Set it empty to skip address lookup. |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated list of origins |
