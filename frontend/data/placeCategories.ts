import { FEATURED_PLACES, type FeaturedGroup } from '~/data/featuredPlaces'

// How each place category is named on the trip page.
export const CATEGORY: Record<string, string> = {
  landmark: 'Landmark', parks: 'Park', hot_springs: 'Hot spring', traditional_food: 'Filipino food',
  seafood: 'Seafood', cafes: 'Café', malls: 'Mall or market', waterfalls: 'Waterfall', farms: 'Farm', other: 'Place',
}

/** The part of the day a stop falls in, from its arrival time ("HH:MM:SS"). */
export function partOfDay(arrive: string): 'morning' | 'afternoon' | 'evening' {
  const h = Number(arrive.slice(0, 2))
  return h < 12 ? 'morning' : h < 17 ? 'afternoon' : 'evening'
}

/** Which drawn picture a place gets, by category, and the hand-picked motif for featured places. */
export const PICTURE_GROUP: Record<string, FeaturedGroup> = {
  landmark: 'landmarks', malls: 'landmarks', other: 'landmarks', hot_springs: 'hot_springs',
  traditional_food: 'food', seafood: 'food', cafes: 'food', parks: 'nature', waterfalls: 'nature', farms: 'nature',
}
export const PICTURE_MOTIF = Object.fromEntries(FEATURED_PLACES.map(p => [p.id, p.motif]))

// Places to visit and places to eat are counted apart, because "3 places a day" does not
// count meals. Seeing "5 stops" for a 3-place day with lunch and dinner reads like a mistake.
// A meal stop is told by its reason ("Lunch near ...") as well as its category, because some
// restaurants have no category yet and show as "Place".
type Eatable = { place: { category: string }; reason?: string }
export const isEatStop = (s: Eatable) =>
  PICTURE_GROUP[s.place.category] === 'food' || /^(breakfast|lunch|dinner)\b/i.test(s.reason ?? '')

export function countStops(stops: Eatable[]) {
  const eats = stops.filter(isEatStop).length
  return { places: stops.length - eats, eats }
}

export function stopsLabel(stops: Eatable[]) {
  const { places, eats } = countStops(stops)
  const p = `${places} ${places === 1 ? 'place' : 'places'}`
  return eats ? `${p} + ${eats} ${eats === 1 ? 'meal' : 'meals'}` : p
}
