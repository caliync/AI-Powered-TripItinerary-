// Mock itinerary built from real Calamba places in OSM (Sheet: Calamba_All_Places).
// Times, reasons and drive times are illustrative until the backend exists.
import type {
  Accessibility, DayPlan, Itinerary, Leg, LatLng, Place, Stop, SwapCandidate, TripIntake,
} from '~/types/itinerary'
import { STAY_ID } from '~/types/itinerary'
import { encodePolyline6 } from '~/utils/polyline'

const access = (wheelchair: Accessibility['wheelchair'], extra: Partial<Accessibility> = {}): Accessibility => ({
  wheelchair, sensory_friendly: 'unknown', walk_m_estimate: null, rough_terrain: false, sources: ['osm'], ...extra,
})

const place = (id: string, name: string, lat: number, lng: number, category: Place['category'],
  outdoor: boolean, a: Accessibility, hours: string | null = null): Place => ({
  id, name, coords: { lat, lng }, category, outdoor, price_tier: null, accessibility: a,
  opening_hours: hours, hours_verified: false,
})

export const STAY: LatLng = { lat: 14.1960653, lng: 121.1436264 } // Hotel Marciano, Real

const P = {
  shrine: place('osm:way/93587272', 'Rizal Shrine', 14.2134403, 121.1667919, 'landmark', false, access('unknown'), 'Tu-Su 08:00-16:00'),
  church: place('osm:way/87216378', 'Calamba Church', 14.2134337, 121.1674963, 'landmark', false, access('unknown')),
  banga: place('osm:way/746912736', 'Calamba Banga', 14.2141971, 121.1670752, 'landmark', true, access('yes', { sources: ['curated'] })),
  lugaw: place('osm:node/1238550504', 'Aling Inday Lugawan sa Banga', 14.2140037, 121.1667915, 'traditional_food', false, access('unknown')),
  baywalk: place('osm:way/530235297', 'Calamba Baywalk Park', 14.2123167, 121.18708, 'parks', true, access('limited')),
  wildlife: place('osm:way/487112992', 'Laguna Wildlife Park and Rescue Center', 14.1783524, 121.1913897, 'parks', true, access('unknown', { rough_terrain: true })),
  lavista: place('osm:way/170221744', 'La Vista Pansol Resort', 14.1797246, 121.1909036, 'hot_springs', true, access('limited')),
  tita: place('osm:node/1737935263', 'Tita Sally Restaurant', 14.1775624, 121.1848303, 'traditional_food', false, access('unknown')),
  samaral: place('osm:way/530206615', 'Samaral Seafood Restaurant', 14.2013138, 121.1595522, 'seafood', false, access('unknown'), 'Mo-Su 10:00-21:00'),
}

// Drive time is a rough 25 km/h town average plus 3 min parking, until OSRM is reachable.
function leg(from: LatLng, to: LatLng, fromId: string, toId: string, factor = 1): Leg {
  const mid = { lat: (from.lat + to.lat) / 2 + 0.002, lng: (from.lng + to.lng) / 2 }
  const dx = (to.lat - from.lat) * 111_000
  const dy = (to.lng - from.lng) * 108_000
  const distance = Math.round(Math.hypot(dx, dy) * 1.35)
  const mins = 3 + (distance / 1000) * 2.4
  return {
    from_id: fromId, to_id: toId,
    distance_m: distance,
    duration_s: Math.round(mins * 60 * factor),
    traffic_factor: factor,
    geometry: encodePolyline6([from, mid, to]),
  }
}

function day(date: string, cluster: number, stops: Stop[], warnings: DayPlan['warnings'], factors: number[] = []): DayPlan {
  const pts = [STAY, ...stops.map(s => s.place.coords), STAY]
  const ids = [STAY_ID, ...stops.map(s => s.place.id), STAY_ID]
  const legs = pts.slice(1).map((p, i) => leg(pts[i], p, ids[i], ids[i + 1], factors[i] ?? 1))
  const c = stops.reduce((a, s) => ({ lat: a.lat + s.place.coords.lat / stops.length, lng: a.lng + s.place.coords.lng / stops.length }), { lat: 0, lng: 0 })
  return {
    date, cluster_id: cluster, centroid: c, radius_m: 1800, stops, legs,
    total_travel_s: legs.reduce((a, l) => a + l.duration_s, 0), warnings,
  }
}

const stop = (order: number, p: Place, arrive: string, depart: string, reason: string): Stop => {
  const [ah, am] = arrive.split(':').map(Number)
  const [dh, dm] = depart.split(':').map(Number)
  return { order, place: p, arrive: `${arrive}:00`, depart: `${depart}:00`, dwell_min: dh * 60 + dm - (ah * 60 + am), reason }
}

export const MOCK_INTAKE: TripIntake = {
  region: 'calamba',
  stay: { label: 'Hotel Marciano, Real, Calamba', coords: STAY },
  start_date: '2026-12-05',
  end_date: '2026-12-06',
  start_time: '08:00:00',
  places_per_day: 4,
  include_meals: true,
  group: 'duo',
  budget: 'mid',
  access_needs: ['minimal_walking'],
  interests: ['hot_springs', 'traditional_food', 'parks'],
  allow_unverified_access: true,
}

export const MOCK_ITINERARY: Itinerary = {
  id: '6f1c2a54-3b0e-4f7e-9b1a-2d9c8e7f6a10',
  version: 1,
  intake: MOCK_INTAKE,
  stay_coords: STAY,
  generated_at: '2026-11-18T10:00:00+08:00',
  providers: { routing: 'osrm', places: 'osm', llm: null },
  days: [
    day('2026-12-05', 0, [
      stop(0, P.banga, '08:30', '09:00', 'Outdoors and short on walking, so it goes first while it is still cool.'),
      stop(1, P.shrine, '09:05', '10:30', "José Rizal's birthplace. The heart of the old town."),
      stop(2, P.church, '10:35', '11:15', 'Next door to the shrine, where Rizal was baptised.'),
      stop(3, P.lugaw, '11:20', '12:20', 'Local lugaw on the same street, one block from the church.'),
      stop(4, P.baywalk, '16:30', '17:45', 'Lakeside walk for sunset over Laguna de Bay.'),
    ], [
      { code: 'access_unverified', message: 'Rizal Shrine has no step-free access info yet. Call ahead if you use a wheelchair.', place_id: P.shrine.id },
    ]),
    day('2026-12-06', 1, [
      stop(0, P.wildlife, '08:30', '10:00', 'Outdoor visit before the midday heat.'),
      stop(1, P.lavista, '10:15', '13:30', 'Warm spring pools a few minutes from the wildlife park.'),
      stop(2, P.tita, '13:40', '14:40', 'Filipino lunch on the way back down from Pansol.'),
      stop(3, P.samaral, '18:00', '19:15', 'Seafood dinner in bamboo cottages near the highway.'),
    ], [
      { code: 'peak_traffic_leg', message: 'The drive to dinner falls in evening rush hour, so it is planned at 1.6x normal time.', place_id: P.samaral.id },
    ], [1, 1, 1, 1.6, 1]),
  ],
}

export const MOCK_SWAPS: SwapCandidate[] = [
  {
    place: place('osm:node/949611916', 'Bistro Halaan', 14.1941826, 121.1646455, 'seafood', false, access('unknown')),
    delta_travel_s: -240, distance_from_old_m: 900, warnings: [],
  },
  {
    place: place('osm:node/6925822009', 'Dampa Station', 14.1976004, 121.1618119, 'seafood', false, access('unknown'), 'Mo-Su 10:00-22:00'),
    delta_travel_s: 60, distance_from_old_m: 450, warnings: [],
  },
  {
    place: place('osm:node/7293582885', 'Shinkansen Ramen & Izakaya', 14.1976261, 121.1617575, 'other', false, access('unknown')),
    delta_travel_s: 120, distance_from_old_m: 470,
    warnings: [{ code: 'hours_unverified', message: 'Opening hours not confirmed.', place_id: null }],
  },
]

// Sample plan reshaped to the traveller's answers, so mock mode (npm run dev:mock) reacts to the form:
// their stay, dates, start time, number of places and meals. The places themselves stay the sample ones.
const isMeal = (p: Place) => p.category === 'traditional_food' || p.category === 'seafood'
const toMin = (hms: string) => { const [h, m] = hms.split(':').map(Number); return h * 60 + m }
const toHms = (min: number) => `${String(Math.floor(min / 60)).padStart(2, '0')}:${String(min % 60).padStart(2, '0')}:00`
const addDays = (iso: string, n: number) => new Date(Date.parse(`${iso}T00:00:00Z`) + n * 86_400_000).toISOString().slice(0, 10)

export function mockItineraryFor(intake: TripIntake): Itinerary {
  const days = Math.round((Date.parse(intake.end_date) - Date.parse(intake.start_date)) / 86_400_000) + 1
  const shift = toMin(intake.start_time) - toMin('08:00')
  const built = Array.from({ length: days }, (_, i) => {
    const base = MOCK_ITINERARY.days[i % MOCK_ITINERARY.days.length]
    let sights = 0
    const kept = base.stops.filter((s) => {
      if (isMeal(s.place)) return intake.include_meals
      return intake.places_per_day == null || ++sights <= intake.places_per_day
    })
    const stops = kept.map((s, order) => ({
      ...s, order,
      arrive: toHms(toMin(s.arrive) + shift), depart: toHms(toMin(s.depart) + shift),
    }))
    const ids = new Set(stops.map(s => s.place.id))
    const warnings = base.warnings.filter(w => !w.place_id || ids.has(w.place_id))
    return day(addDays(intake.start_date, i), i, stops, warnings)
  })
  const stay = intake.stay.coords ?? STAY
  return { ...MOCK_ITINERARY, intake, stay_coords: stay, days: built }
}
