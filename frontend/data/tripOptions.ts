// Choices shared by the plan page and the trip page.
import { clock } from '~/utils/format'

/** Most places a traveller can ask for in one day (meals come on top). Matches MAX_PLACES_PER_DAY in schema.py. */
export const MAX_PLACES = 6

/** When the day can start, every half hour from 5:00 AM to 12:00 PM (schema.py EARLIEST_START..LATEST_START). */
export const START_TIMES = Array.from({ length: 15 }, (_, i) => {
  const mins = 5 * 60 + i * 30
  const value = `${String(Math.floor(mins / 60)).padStart(2, '0')}:${String(mins % 60).padStart(2, '0')}`
  return { value, label: clock(value) }
})
