// The only file that talks to the backend. By default it calls the real planner
// (FastAPI on :8000, proxied in dev). `npm run dev:mock` turns on `useMocks`, which
// returns sample data after a short delay so loading states are visible in design review.
// The sample trip at /trip/demo always comes from the built-in data, in both modes.
import type {
  ApiError, BusinessSubmission, Itinerary, StaySuggestion, StopAdd, StopChoices, StopRemove, SwapApply, SwapCandidate,
  SwapRequest, TripIntake,
} from '~/types/itinerary'
import { MOCK_ITINERARY, MOCK_SWAPS, mockItineraryFor } from '~/data/mockItinerary'

// A few real Calamba stays for `npm run dev:mock`.
const MOCK_STAYS: StaySuggestion[] = [
  { name: 'Hotel Marciano', kind: 'hotel', coords: { lat: 14.19607, lng: 121.14363 } },
  { name: 'Astrotel', kind: 'hotel', coords: { lat: 14.20567, lng: 121.15450 } },
  { name: 'Hotel Oliva 88', kind: 'hotel', coords: { lat: 14.21165, lng: 121.13311 } },
  { name: 'Villa Aleta', kind: 'hotel', coords: { lat: 14.17825, lng: 121.18327 } },
]

const wait = (ms: number) => new Promise(r => setTimeout(r, ms))

/** The id of the built-in sample trip. The API never has it, so it is always served locally. */
export const DEMO_TRIP_ID = 'demo'

/** A failure the page can act on. `message` is written for the traveller when the API sent one. */
export class TripApiError extends Error {
  constructor(public code: string, message: string, public status?: number) {
    super(message)
  }
}

function toApiError(e: unknown): TripApiError {
  const err = e as { statusCode?: number; data?: Partial<ApiError> }
  const detail = err?.data?.detail
  if (detail?.code) return new TripApiError(detail.code, detail.message ?? '', err.statusCode)
  if (err?.statusCode === 404) return new TripApiError('not_found', '', 404)
  return new TripApiError('network', '', err?.statusCode)
}

export function useTripApi() {
  const { apiBase, useMocks } = useRuntimeConfig().public
  // In mock mode the plan made from the traveller's answers is kept here, so the trip page shows it.
  const mockTrip = useState<Itinerary | null>('mock-trip', () => null)

  async function call<T>(path: string, body?: unknown): Promise<T> {
    try {
      return await $fetch<T>(`${apiBase}${path}`, body === undefined ? {} : { method: 'POST', body })
    } catch (e) {
      throw toApiError(e)
    }
  }

  async function generate(intake: TripIntake): Promise<Itinerary> {
    if (useMocks) {
      await wait(900)
      mockTrip.value = mockItineraryFor(intake)
      return mockTrip.value
    }
    return call<Itinerary>('/itinerary/generate', intake)
  }

  const local = (id: string) => useMocks || id === DEMO_TRIP_ID

  async function get(id: string): Promise<Itinerary> {
    if (local(id)) {
      await wait(500)
      if (id === 'missing') throw new TripApiError('not_found', '', 404)
      return id !== DEMO_TRIP_ID && mockTrip.value ? mockTrip.value : MOCK_ITINERARY
    }
    return call<Itinerary>(`/itinerary/${id}`)
  }

  async function swapOptions(id: string, req: SwapRequest): Promise<SwapCandidate[]> {
    if (local(id)) {
      await wait(600)
      return MOCK_SWAPS
    }
    return call<SwapCandidate[]>(`/itinerary/${id}/swap`, req)
  }

  /** Places to pick from for each stop of one day (Morning, Afternoon, Evening). */
  async function dayChoices(id: string, dayIndex: number): Promise<StopChoices[]> {
    if (local(id)) {
      await wait(500)
      const stops = (mockTrip.value ?? MOCK_ITINERARY).days[dayIndex]?.stops ?? []
      return stops.map((s, i) => ({ stop_order: s.order, options: i === 0 ? MOCK_SWAPS.slice(0, 3) : [] }))
    }
    return call<StopChoices[]>(`/itinerary/${id}/days/${dayIndex}/choices`)
  }

  async function applySwap(id: string, body: SwapApply): Promise<Itinerary> {
    if (local(id)) {
      await wait(500)
      const it = structuredClone(id !== DEMO_TRIP_ID && mockTrip.value ? mockTrip.value : MOCK_ITINERARY)
      const pick = MOCK_SWAPS.find(c => c.place.id === body.new_place_id)
      if (pick) it.days[body.day_index].stops[body.stop_order].place = pick.place
      it.version = body.version + 1
      return it
    }
    return call<Itinerary>(`/itinerary/${id}/swap/apply`, body)
  }

  /** Places near one day's route that can be added to it. */
  async function dayRecommendations(id: string, dayIndex: number): Promise<SwapCandidate[]> {
    if (local(id)) {
      await wait(400)
      return MOCK_SWAPS
    }
    return call<SwapCandidate[]>(`/itinerary/${id}/days/${dayIndex}/recommendations`)
  }

  /** The sample plan keeps its times as they are; the real planner rebuilds the whole day. */
  const sample = (id: string) => structuredClone(id !== DEMO_TRIP_ID && mockTrip.value ? mockTrip.value : MOCK_ITINERARY)
  const renumber = (it: Itinerary, day: number) => it.days[day].stops.forEach((s, i) => (s.order = i))

  async function addStop(id: string, body: StopAdd): Promise<Itinerary> {
    if (local(id)) {
      await wait(500)
      const it = sample(id)
      const pick = MOCK_SWAPS.find(c => c.place.id === body.new_place_id)
      const stops = it.days[body.day_index].stops
      const at = { morning: 1, afternoon: Math.max(1, stops.length - 1), evening: stops.length }[body.part]
      if (pick) stops.splice(at, 0, { ...structuredClone(stops[0]), place: pick.place })
      renumber(it, body.day_index)
      it.version = body.version + 1
      return it
    }
    return call<Itinerary>(`/itinerary/${id}/stops/add`, body)
  }

  async function removeStop(id: string, body: StopRemove): Promise<Itinerary> {
    if (local(id)) {
      await wait(400)
      const it = sample(id)
      it.days[body.day_index].stops.splice(body.stop_order, 1)
      renumber(it, body.day_index)
      it.version = body.version + 1
      return it
    }
    return call<Itinerary>(`/itinerary/${id}/stops/remove`, body)
  }

  async function submitBusiness(body: BusinessSubmission): Promise<{ status: 'pending' }> {
    if (useMocks) {
      await wait(700)
      return { status: 'pending' }
    }
    return call<{ status: 'pending' }>('/places/submissions', body)
  }

  /** Stays that fit what the traveller has typed. Suggestions are a help, so failures give none. */
  async function suggestStays(q: string): Promise<StaySuggestion[]> {
    if (useMocks) {
      const t = q.toLowerCase()
      return MOCK_STAYS.filter(s => s.name.toLowerCase().split(' ').some(w => w.startsWith(t.split(' ')[0])))
    }
    try {
      return await $fetch<StaySuggestion[]>(`${apiBase}/stays/suggest`, { query: { q } })
    } catch {
      return []
    }
  }

  return { generate, get, swapOptions, dayChoices, dayRecommendations, addStop, removeStop, applySwap, submitBusiness, suggestStays }
}
