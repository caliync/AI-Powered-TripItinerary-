// Suggestions for "where are you staying" from our hotels, guest houses and resorts, shared by
// the home page form and the plan page. Typing "Mar" offers Hotel Marciano; picking one also
// gives its location. Typing anything else still works.
import type { LatLng, StaySuggestion } from '~/types/itinerary'

export const STAY_KIND: Record<string, string> = {
  hotel: 'Hotel', guest_house: 'Guest house', resort: 'Resort', water_park: 'Resort',
  swimming_pool: 'Private pool', curated: 'Place',
}

export function useStaySuggest(label: Ref<string>, coords: Ref<LatLng | null>) {
  const api = useTripApi()
  const options = ref<StaySuggestion[]>([])
  const open = ref(false)
  const active = ref(-1)
  let timer: ReturnType<typeof setTimeout> | undefined
  let lastQuery = ''

  function onInput() {
    coords.value = null // typed text no longer matches a picked place
    clearTimeout(timer)
    timer = setTimeout(lookUp, 150)
  }

  async function lookUp() {
    const q = label.value.trim()
    lastQuery = q
    const found = q.length >= 2 ? await api.suggestStays(q) : []
    if (q !== lastQuery) return // a newer search started
    options.value = found
    active.value = -1
    open.value = found.length > 0
  }

  function pick(s: StaySuggestion) {
    label.value = s.name
    coords.value = s.coords
    open.value = false
  }

  function onKey(e: KeyboardEvent) {
    if (!open.value || !options.value.length) return
    const n = options.value.length
    if (e.key === 'ArrowDown') { e.preventDefault(); active.value = (active.value + 1) % n }
    else if (e.key === 'ArrowUp') { e.preventDefault(); active.value = (active.value - 1 + n) % n }
    else if (e.key === 'Enter' && active.value >= 0) { e.preventDefault(); pick(options.value[active.value]) }
    else if (e.key === 'Escape') open.value = false
  }

  // Let a click on a suggestion land before the list closes.
  function onBlur() { setTimeout(() => (open.value = false), 120) }
  function onFocus() { open.value = options.value.length > 0 }

  return { options, open, active, onInput, pick, onKey, onBlur, onFocus }
}
