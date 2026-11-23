<script setup lang="ts">
// "Where are you staying?" with suggestions from our hotels, guest houses and resorts while
// the traveller types ("Mar" offers Hotel Marciano). Picking one also fills in its location,
// so the planner doesn't have to look it up. Typing anything else still works.
import type { LatLng } from '~/types/itinerary'

const label = defineModel<string>({ required: true })
const coords = defineModel<LatLng | null>('coords', { required: true })
defineProps<{ invalid?: boolean }>()

const { options, open, active, onInput, pick, onKey, onBlur, onFocus } = useStaySuggest(label, coords)
</script>

<template>
  <div class="relative">
    <label class="block text-sm font-medium" for="stay">Hotel, resort or address</label>
    <input id="stay" v-model="label" type="text" autocomplete="off" placeholder="Start typing, e.g. Hotel Marciano"
      role="combobox" aria-autocomplete="list" aria-controls="stay-options" :aria-expanded="open"
      :aria-activedescendant="active >= 0 ? `stay-option-${active}` : undefined" :aria-invalid="invalid || undefined"
      class="mt-1 w-full rounded-[12px] border border-line bg-surface px-4 py-3.5 shadow-sm focus:border-lake focus:ring-2 focus:ring-lake/25 outline-none"
      @input="onInput" @keydown="onKey" @blur="onBlur" @focus="onFocus">
    <ul v-show="open" id="stay-options" role="listbox" aria-label="Places to stay"
      class="absolute z-20 mt-2 w-full overflow-hidden rounded-[14px] border border-line bg-surface shadow-lift">
      <li v-for="(s, i) in options" :id="`stay-option-${i}`" :key="s.name + i" role="option" :aria-selected="i === active"
        class="flex cursor-pointer items-center justify-between gap-3 px-4 py-3 text-[15px]"
        :class="i === active ? 'bg-lake-soft' : 'hover:bg-soft'"
        @mousedown.prevent="pick(s)">
        <span class="flex items-center gap-3 min-w-0">
          <svg class="shrink-0 text-lake" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M12 21s-6.5-5.6-6.5-11a6.5 6.5 0 0 1 13 0C18.5 15.4 12 21 12 21Z" /><circle cx="12" cy="10" r="2.4" /></svg>
          <span class="truncate font-medium">{{ s.name }}</span>
        </span>
        <span class="shrink-0 text-sm text-muted">{{ STAY_KIND[s.kind] ?? 'Place' }}</span>
      </li>
    </ul>
    <p v-if="coords" class="mt-2 text-sm text-moss">Found on the map.</p>
  </div>
</template>
