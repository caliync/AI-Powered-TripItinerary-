// Intake form state + validation. Mirrors TripIntake rules in backend/app/schema.py.
import type { AccessNeed, BudgetTier, GroupSize, LatLng, TripIntake } from '~/types/itinerary'
import { detectInterests } from '~/data/interestWords'

const MAX_TRIP_DAYS = 14

// Typed budget -> tier, by pesos per person per day. Placeholder lines until Alli sets them;
// the amount itself is sent too (budget_php) for real estimates later.
export const BUDGET_LINES = { mid: 1500, premium: 4000 }
export const TIER_LABEL: Record<BudgetTier, string> = { budget: 'budget', mid: 'mid-range', premium: 'premium' }

export function useIntakeForm() {
  const form = reactive({
    stayLabel: '',
    stayCoords: null as LatLng | null,
    startDate: '',
    endDate: '', // optional: blank means a one-day trip
    startTime: '08:00', // when they leave their stay each morning
    group: '' as GroupSize | '',
    groupCount: 4,
    budgetText: '',
    placesPerDay: 4, // places to visit each day, not counting meals
    includeFood: true, // false = they bring their own food, so no lunch or dinner stops
    accessNeeds: [] as AccessNeed[],
    interestsText: '',
  })
  const touched = ref(false)

  const lastDay = computed(() => form.endDate || form.startDate)
  const tripDays = computed(() => {
    if (!form.startDate) return 0
    return Math.max(0, (Date.parse(lastDay.value) - Date.parse(form.startDate)) / 86_400_000 + 1)
  })
  const people = computed(() => (form.group === 'solo' ? 1 : form.group === 'duo' ? 2 : form.group === 'group' ? form.groupCount : 0))

  /** Pesos as typed ("₱6,000" or "6000"), or null. */
  const budgetPhp = computed(() => {
    const digits = form.budgetText.replace(/[^\d]/g, '')
    const n = Math.round(Number(digits))
    return digits && Number.isFinite(n) && n > 0 ? n : null
  })
  const perPersonDay = computed(() =>
    budgetPhp.value && people.value && tripDays.value ? Math.round(budgetPhp.value / (people.value * tripDays.value)) : null)
  const budgetTier = computed<BudgetTier | null>(() => {
    const v = perPersonDay.value
    if (v === null) return null
    return v >= BUDGET_LINES.premium ? 'premium' : v >= BUDGET_LINES.mid ? 'mid' : 'budget'
  })

  const interests = computed(() => detectInterests(form.interestsText))

  const today = todayInManila()
  const errors = computed(() => {
    const e: Partial<Record<'stay' | 'dates' | 'group' | 'budget', string>> = {}
    if (!form.stayLabel.trim()) e.stay = 'Enter where you are staying.'
    if (!form.startDate) e.dates = 'Pick your arrival date.'
    else if (form.startDate < today) e.dates = 'Arrival can’t be in the past.'
    else if (tripDays.value < 1) e.dates = 'Leaving must be on or after arriving.'
    else if (tripDays.value > MAX_TRIP_DAYS) e.dates = `Trips can be up to ${MAX_TRIP_DAYS} days.`
    if (!form.group) e.group = 'Choose who is travelling.'
    else if (form.group === 'group' && (form.groupCount < 3 || form.groupCount > 30)) e.group = 'Groups are 3 to 30 people.'
    if (!budgetPhp.value) e.budget = 'Type your budget in pesos.'
    return e
  })

  const isValid = computed(() => Object.keys(errors.value).length === 0)

  function toIntake(): TripIntake {
    return {
      region: 'calamba',
      stay: { label: form.stayLabel.trim(), coords: form.stayCoords },
      start_date: form.startDate,
      end_date: lastDay.value,
      start_time: form.startTime,
      group: form.group as GroupSize,
      group_count: form.group === 'group' ? form.groupCount : null,
      budget: budgetTier.value ?? 'mid',
      budget_php: budgetPhp.value,
      places_per_day: form.placesPerDay,
      include_meals: form.includeFood,
      access_needs: form.accessNeeds,
      interests: interests.value,
      interests_text: form.interestsText.trim() || null,
      allow_unverified_access: true,
    }
  }

  return { form, errors, touched, isValid, tripDays, budgetPhp, perPersonDay, budgetTier, interests, today, toIntake }
}
