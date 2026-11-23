<script setup lang="ts">
// "More places near your route": a filterable grid. Each card adds the place to the morning,
// afternoon or evening in one tap. The name opens a short detail panel.
import type { SwapCandidate } from '~/types/itinerary'
import { CATEGORY, PICTURE_GROUP, PICTURE_MOTIF } from '~/data/placeCategories'
import { HOT_SPRING_FROM_PHP } from '~/data/costs'

type Part = 'morning' | 'afternoon' | 'evening'
const props = defineProps<{ items: SwapCandidate[]; loading: boolean; applying: boolean; full: boolean }>()
const emit = defineEmits<{ add: [SwapCandidate, Part] }>()

const PARTS: { id: Part; label: string }[] = [
  { id: 'morning', label: 'Morning' }, { id: 'afternoon', label: 'Afternoon' }, { id: 'evening', label: 'Evening' },
]
const FILTERS = [
  { id: 'all', label: 'All', groups: null },
  { id: 'landmarks', label: 'Landmarks', groups: ['landmarks'] },
  { id: 'food', label: 'Food', groups: ['food'] },
  { id: 'nature', label: 'Nature', groups: ['nature'] },
  { id: 'hot_springs', label: 'Hot springs', groups: ['hot_springs'] },
] as const

const filter = ref<string>('all')
const sort = ref<'closest' | 'name'>('closest')
const PAGE = 12
const shown = ref(PAGE)
const open = ref<SwapCandidate | null>(null)

const groupOf = (it: SwapCandidate) => PICTURE_GROUP[it.place.category] ?? 'landmarks'
const available = computed(() => FILTERS.filter(f => f.groups === null || props.items.some(i => (f.groups as readonly string[]).includes(groupOf(i)))))
const list = computed(() => {
  const f = FILTERS.find(x => x.id === filter.value)
  const rows = props.items.filter(i => !f?.groups || (f.groups as readonly string[]).includes(groupOf(i)))
  return [...rows].sort((a, b) => sort.value === 'name' ? a.place.name.localeCompare(b.place.name) : a.delta_travel_s - b.delta_travel_s)
})
const visible = computed(() => list.value.slice(0, shown.value))
watch([filter, sort], () => (shown.value = PAGE))
watch(() => props.items.map(i => i.place.id).join(), () => { shown.value = PAGE; open.value = null })

const priceNote = (it: SwapCandidate) =>
  it.place.category === 'hot_springs' ? `Usually from ${pesos(HOT_SPRING_FROM_PHP)} per person` : null
const kind = (it: SwapCandidate) => CATEGORY[it.place.category]
const extra = (it: SwapCandidate) => signedMinutes(it.delta_travel_s).toLowerCase()

function add(it: SwapCandidate, part: Part) {
  open.value = null
  emit('add', it, part)
}
</script>

<template>
  <section class="mt-12" aria-labelledby="more-places">
    <div v-if="loading" class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3" aria-hidden="true">
      <div v-for="n in 3" :key="n" class="h-[360px] rounded-[18px] bg-soft animate-pulse" />
    </div>
    <template v-else-if="items.length">
      <div class="flex flex-wrap items-end gap-x-4 gap-y-2">
        <div>
          <h2 id="more-places" class="text-2xl font-extrabold tracking-tight">More places near your route</h2>
          <p class="text-sm text-muted">Add one to the morning, afternoon or evening. {{ items.length }} places.</p>
        </div>
        <label class="ml-auto flex items-center gap-2 text-sm text-muted">
          Sort
          <select v-model="sort" class="rounded-pill border border-line bg-surface px-3 min-h-[40px] font-semibold text-ink">
            <option value="closest">Closest first</option>
            <option value="name">A to Z</option>
          </select>
        </label>
      </div>

      <div class="mt-4 flex flex-wrap gap-2" role="group" aria-label="Filter by type">
        <button v-for="f in available" :key="f.id" type="button" :aria-pressed="filter === f.id"
          class="rounded-pill border px-4 min-h-[40px] text-sm font-semibold transition-colors"
          :class="filter === f.id ? 'border-lake bg-lake text-surface' : 'border-line bg-surface hover:border-ink/40'"
          @click="filter = f.id">{{ f.label }}</button>
      </div>

      <p v-if="full" class="mt-4 rounded-[12px] bg-soft border border-line px-4 py-3 text-sm text-muted">This day is full. Remove a place to add another.</p>

      <ul v-if="visible.length" class="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <li v-for="it in visible" :key="it.place.id">
          <article class="h-full flex flex-col overflow-hidden rounded-[18px] border border-line bg-surface shadow-sm hover:shadow-lift transition-shadow">
            <div class="h-36">
              <PlaceThumb :group="groupOf(it)" :motif="PICTURE_MOTIF[it.place.id]" :seed="it.place.name.length" />
            </div>
            <div class="flex flex-1 flex-col p-4">
              <h3 class="text-lg font-extrabold tracking-tight leading-snug">
                <button type="button" class="text-left hover:underline" @click="open = it">{{ it.place.name }}</button>
              </h3>
              <p class="mt-0.5 text-sm text-muted">{{ kind(it) }}, {{ extra(it) }}</p>
              <p v-if="priceNote(it)" class="mt-1 text-sm font-medium">{{ priceNote(it) }}</p>
              <div class="mt-2">
                <AccessBadge :status="it.place.accessibility.wheelchair" :rough="it.place.accessibility.rough_terrain" />
              </div>
              <div class="mt-auto pt-4" role="group" :aria-label="`Add ${it.place.name} to your day`">
                <p class="text-xs font-semibold text-muted">Add to</p>
                <div class="mt-1.5 grid grid-cols-3 gap-2">
                  <button v-for="part in PARTS" :key="part.id" type="button" :disabled="applying || full"
                    class="rounded-[12px] border border-line bg-surface hover:border-lake hover:bg-lake-soft px-1 min-h-[40px] text-[13px] font-semibold whitespace-nowrap disabled:opacity-50 disabled:hover:bg-surface disabled:hover:border-line"
                    @click="add(it, part.id)">{{ part.label }}</button>
                </div>
              </div>
            </div>
          </article>
        </li>
      </ul>
      <p v-else class="mt-5 text-muted">No more places match. Try All.</p>

      <div v-if="list.length > shown" class="mt-6 text-center">
        <button type="button" class="rounded-pill border border-line bg-surface px-6 min-h-[44px] font-semibold hover:border-ink/40"
          @click="shown += PAGE">Show {{ Math.min(PAGE, list.length - shown) }} more</button>
      </div>

      <!-- Place detail panel -->
      <div v-if="open" class="fixed inset-0 z-[1300] grid place-items-end sm:place-items-center bg-ink/50 p-0 sm:p-6" @click.self="open = null"
        @keydown.esc="open = null">
        <div role="dialog" aria-modal="true" :aria-label="open.place.name" class="w-full sm:max-w-md overflow-hidden rounded-t-[24px] sm:rounded-[24px] bg-surface shadow-lift">
          <div class="h-44">
            <PlaceThumb :group="groupOf(open)" :motif="PICTURE_MOTIF[open.place.id]" :seed="open.place.name.length" />
          </div>
          <div class="p-5">
            <div class="flex items-start gap-3">
              <h3 class="text-2xl font-extrabold tracking-tight leading-snug">{{ open.place.name }}</h3>
              <button type="button" autofocus class="ml-auto grid h-10 w-10 shrink-0 place-items-center rounded-pill border border-line hover:bg-soft" aria-label="Close" @click="open = null">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18" /></svg>
              </button>
            </div>
            <p class="mt-1 text-muted">{{ kind(open) }}, {{ extra(open) }}</p>
            <p v-if="priceNote(open)" class="mt-3 font-medium">{{ priceNote(open) }}. Fee not confirmed.</p>
            <p v-if="open.place.opening_hours" class="mt-2 text-sm text-muted">Listed hours {{ open.place.opening_hours }}, not confirmed</p>
            <div class="mt-3"><AccessBadge :status="open.place.accessibility.wheelchair" :rough="open.place.accessibility.rough_terrain" /></div>
            <p class="mt-5 text-sm font-semibold">Add to</p>
            <div class="mt-2 grid grid-cols-3 gap-2">
              <button v-for="part in PARTS" :key="part.id" type="button" :disabled="applying || full"
                class="rounded-[12px] bg-lake text-surface hover:bg-lake-deep px-2 min-h-[44px] text-sm font-semibold disabled:opacity-50"
                @click="add(open, part.id)">{{ part.label }}</button>
            </div>
          </div>
        </div>
      </div>
    </template>
  </section>
</template>
