<script setup lang="ts">
// One stop on the ribbon. The numbered dot sits on the mango line.
import type { Stop } from '~/types/itinerary'
import { CATEGORY, PICTURE_GROUP as GROUP, PICTURE_MOTIF as MOTIF, isEatStop } from '~/data/placeCategories'
const props = defineProps<{ stop: Stop; note?: string; busy?: boolean; selected?: boolean; cost?: string }>()
defineEmits<{ remove: []; select: [] }>()
// Restaurants without a category used to show as "Place" with a church picture.
const eats = computed(() => isEatStop(props.stop))
const kind = computed(() => {
  const known = CATEGORY[props.stop.place.category]
  if (!eats.value || (known && props.stop.place.category !== 'other')) return known
  return /^dinner/i.test(props.stop.reason) ? 'Dinner' : /^lunch/i.test(props.stop.reason) ? 'Lunch' : 'Meal'
})
const picture = computed(() => eats.value ? 'food' : (GROUP[props.stop.place.category] ?? 'landmarks'))
</script>

<template>
  <article :id="`stop-${stop.order}`" class="relative pl-12" @click="$emit('select')">
    <span class="absolute left-0 top-4 grid h-9 w-9 place-items-center rounded-pill bg-mango text-[#15262b] font-extrabold ring-4 ring-bg">
      {{ stop.order + 1 }}
    </span>
    <div class="rounded-[20px] border bg-surface p-4 sm:p-5 shadow-sm hover:shadow-lift transition-shadow cursor-pointer sm:grid sm:grid-cols-[1fr_9.5rem] sm:gap-5"
      :class="selected ? 'border-lake ring-2 ring-lake' : 'border-line'">
      <div class="min-w-0">
      <div class="flex flex-wrap items-center gap-2">
        <p class="rounded-pill bg-lake-soft px-3 py-1 text-sm font-bold tabular-nums text-lake-deep">{{ clock(stop.arrive) }} to {{ clock(stop.depart) }}</p>
        <p class="rounded-pill border border-line px-3 py-1 text-sm text-muted">{{ kind }}, {{ minutes(stop.dwell_min * 60) }} here</p>
      </div>
      <div class="mt-1 flex items-start gap-3">
        <h3 class="text-[22px] font-extrabold tracking-tight leading-snug">{{ stop.place.name }}</h3>
        <button type="button" :disabled="busy"
          class="ml-auto -mt-0.5 shrink-0 inline-flex items-center gap-1.5 rounded-pill px-3 min-h-[36px] text-sm font-semibold text-muted hover:text-danger hover:bg-soft disabled:opacity-50"
          :aria-label="`Remove ${stop.place.name} from your plan`" @click.stop="$emit('remove')">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18" /></svg>
          Remove
        </button>
      </div>
      <p class="mt-1 text-muted max-w-[60ch]">{{ stop.reason }}</p>
      <p v-if="cost" class="mt-1 text-sm font-medium">{{ cost }}</p>
      <div class="mt-3 flex flex-wrap items-center gap-2">
        <AccessBadge :status="stop.place.accessibility.wheelchair" :rough="stop.place.accessibility.rough_terrain" />
        <span v-if="stop.place.opening_hours && !stop.place.hours_verified" class="text-xs text-muted">
          Listed hours {{ stop.place.opening_hours }}, not confirmed
        </span>
      </div>
      <p v-if="note" class="mt-3 rounded-[12px] bg-mango/10 border border-mango/30 px-3 py-2 text-sm">{{ note }}</p>
      </div>
      <div class="hidden sm:block row-span-1 h-[9.5rem] w-[9.5rem] overflow-hidden rounded-[16px]">
        <PlaceThumb :group="picture" :motif="MOTIF[stop.place.id]" :seed="stop.order + stop.place.name.length" />
      </div>
    </div>
  </article>
</template>
