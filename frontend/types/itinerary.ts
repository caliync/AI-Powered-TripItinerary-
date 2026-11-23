// Trip types for the website. Do not hand-edit the shapes here: they come from
// the backend's Pydantic models (backend/app/schema.py) through
//   backend/scripts/export_openapi.py -> types/openapi.json -> types/api.gen.ts
// Run `npm run types:gen` after changing the backend. CI fails if they drift.
import type { components } from './api.gen'

type S = components['schemas']
/** Fields the server fills with a default when the website leaves them out. */
type WithDefaults<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>

export type RegionId = S['RegionId']
export type GroupSize = S['GroupSize']
export type BudgetTier = S['BudgetTier']
export type AccessNeed = S['AccessNeed']
export type Interest = S['Interest']
export type AccessStatus = S['AccessStatus']
export type WarningCode = S['WarningCode']
export type PlaceId = string

export type LatLng = S['LatLng']
export type StayLocation = S['StayLocation']
export type StaySuggestion = S['StaySuggestion']
export type TripIntake = S['TripIntake']
export type Accessibility = S['Accessibility']
export type Place = S['Place']
export type ItineraryWarning = S['ItineraryWarning']
export type Leg = S['Leg']
export type Stop = S['Stop']
/** legs.length === stops.length + 1 (stay -> stops -> stay), or 0 on a free day */
export type DayPlan = S['DayPlan']
export type Providers = S['Providers']
export type Itinerary = S['Itinerary']
export type SwapRequest = WithDefaults<S['SwapRequest'], 'radius_m' | 'exclude_ids'>
export type SwapCandidate = S['SwapCandidate']
export type SwapApply = S['SwapApply']
export type StopChoices = S['StopChoices']
export type StopAdd = S['StopAdd']
export type StopRemove = S['StopRemove']
export type BusinessSubmission = S['Submission']
export type ApiError = S['ErrorBody']

// Constants mirrored from backend/app/schema.py (OpenAPI carries types, not constants).
export const STAY_ID = 'stay' as const
export const SWAP_RADIUS_MIN_M = 3000
export const SWAP_RADIUS_MAX_M = 5000
export const MAX_STOPS_PER_DAY = 8
