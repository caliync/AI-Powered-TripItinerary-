// Words that tell us what a traveller wants to see, for the "What places are you thinking
// about?" box. Matching is simple keyword search for now (no AI in the beta); an AI step can
// replace detectInterests() later without changing the form.
import type { Interest } from '~/types/itinerary'

export const INTEREST_LABELS: Record<Interest, string> = {
  hot_springs: 'Hot springs & resorts',
  traditional_food: 'Filipino food',
  seafood: 'Seafood',
  cafes: 'Cafés',
  parks: 'Parks & nature',
  malls: 'Malls & markets',
  waterfalls: 'Waterfalls',
  farms: 'Farms',
}

// English and Tagalog words. Each word matches at the start of a word ("spring" finds "springs").
const WORDS: Record<Interest, string[]> = {
  hot_springs: ['hot spring', 'hotspring', 'spring', 'resort', 'pool', 'swim', 'pansol', 'bukal', 'spa', 'ligo', 'paligo'],
  traditional_food: ['filipino', 'pinoy', 'local food', 'food', 'carinderia', 'karinderya', 'kainan', 'lutong bahay', 'buko pie', 'kakanin', 'lechon', 'pancit', 'adobo', 'ulam', 'eat'],
  seafood: ['seafood', 'sea food', 'fish', 'isda', 'shrimp', 'hipon', 'crab', 'alimango', 'tilapia', 'bangus', 'paluto'],
  cafes: ['cafe', 'coffee', 'kape', 'kapihan', 'milk tea', 'tea', 'dessert', 'pastry', 'bakery', 'panaderya'],
  parks: ['park', 'nature', 'garden', 'forest', 'mountain', 'makiling', 'hike', 'hiking', 'trail', 'view', 'picnic', 'outdoor', 'bundok'],
  malls: ['mall', 'market', 'palengke', 'shopping', 'shop', 'pasalubong', 'tiangge', 'store'],
  waterfalls: ['waterfall', 'falls', 'talon', 'cascade'],
  farms: ['farm', 'bukid', 'orchard', 'plantation', 'ranch', 'petting', 'animals', 'fruit picking'],
}

const normalize = (s: string) => s.normalize('NFKD').replace(/[̀-ͯ]/g, '').toLowerCase()
const escape = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
const PATTERNS = Object.entries(WORDS).map(([interest, words]) => ({
  interest: interest as Interest,
  re: new RegExp(`(^|[^a-z])(${words.map(escape).join('|')})`),
}))

/** The interests found in what the traveller typed, in the order of INTEREST_LABELS. */
export function detectInterests(text: string): Interest[] {
  const t = normalize(text)
  if (!t.trim()) return []
  return PATTERNS.filter(p => p.re.test(t)).map(p => p.interest)
}
