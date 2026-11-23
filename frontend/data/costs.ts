// Rough cost guides shown on the trip page. Only what we have a source for:
// meals (public Calamba averages from Numbeo and CityCost, Nov 2026: about 250 a budget meal,
// about 375 each at a mid-range sit-down) and hot springs (Alli: usually from 800 a head).
// Landmarks, parks, malls, markets and other open places get no price on purpose.
import type { Stop } from '~/types/itinerary'
import { isEatStop } from '~/data/placeCategories'

export const MEAL_PHP = { budget: 250, mid: 375, premium: 375 } as const
export const HOT_SPRING_FROM_PHP = 800

export type Cost = { each: number; open: boolean; text: string } | null

/** Per-person cost guide for one stop, or null when we don't price it. */
export function stopCost(s: Stop, tier: keyof typeof MEAL_PHP): Cost {
  if (s.place.category === 'hot_springs')
    return { each: HOT_SPRING_FROM_PHP, open: true, text: `Entrance usually from ${pesos(HOT_SPRING_FROM_PHP)} per person. Fee not confirmed.` }
  if (isEatStop(s)) {
    const each = MEAL_PHP[tier]
    return { each, open: tier === 'premium', text: `About ${pesos(each)}${tier === 'premium' ? ' or more' : ''} per person. An estimate, not this menu’s prices.` }
  }
  return null
}

/** What the priced stops of a day add up to for the group. */
export function dayCost(stops: Stop[], tier: keyof typeof MEAL_PHP, people: number) {
  const priced = stops.map(s => stopCost(s, tier)).filter((c): c is NonNullable<Cost> => !!c)
  return { total: priced.reduce((n, c) => n + c.each, 0) * people, from: priced.some(c => c.open), count: priced.length }
}
