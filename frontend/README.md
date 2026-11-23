# Calamba Trip Planner, frontend

This is the Nuxt 3, Vue 3, TypeScript and Tailwind template for the beta. It covers Calamba only and plans car trips.

```bash
npm install
npm run dev        # http://localhost:3000
npm run typecheck
npm run build
```

## Pages

| Route | What it is |
| --- | --- |
| `/` | Trip intake: stay and dates, who's going, budget, access needs, interests |
| `/trip/:id` | The plan, with day tabs, the route ribbon, a Leaflet map and the swap panel. `/trip/demo` shows sample data and `/trip/missing` shows the not-found state. |
| `/business` | A form for owners to add their place. Every entry is reviewed by a person. |

## Backend

All backend calls go through `composables/useTripApi.ts`. By default they go to the real planner: start the backend first (see `backend/README.md`), then `npm run dev`, which proxies `/api` to port 8000. To design without the backend, run `npm run dev:mock`; it shows sample data from `data/mockItinerary.ts`. The sample trip at `/trip/demo` always uses that sample data. The types in `types/itinerary.ts` mirror `backend/app/schema.py`.

Map data © OpenStreetMap contributors (ODbL). Drive times will come from OSRM.
