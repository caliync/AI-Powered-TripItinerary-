<script setup lang="ts">
// The plan: day tabs, a route ribbon (stay, stops, back to stay), and a map.
import type { Itinerary, Stop, SwapCandidate } from '~/types/itinerary'
import { MAX_STOPS_PER_DAY } from '~/types/itinerary'
import { isEatStop, partOfDay, stopsLabel } from '~/data/placeCategories'
import { dayCost, stopCost } from '~/data/costs'

const route = useRoute()
const api = useTripApi()
const id = computed(() => String(route.params.id))

const state = ref<'loading' | 'error' | 'missing' | 'ready'>('loading')
const plan = ref<Itinerary | null>(null)
const dayIndex = ref(0)
const applying = ref(false)
const toast = ref('')
const toastUndo = ref<null | (() => void)>(null)
const mapOpen = ref(false) // phone: the map is a sheet
const selected = ref<number | null>(null) // the stop picked on the list or the map

async function load() {
  state.value = 'loading'
  try {
    plan.value = await api.get(id.value)
    state.value = 'ready'
  } catch (e) {
    state.value = e instanceof TripApiError && e.code === 'not_found' ? 'missing' : 'error'
  }
}
onMounted(load)

const day = computed(() => plan.value?.days[dayIndex.value] ?? null)
const noteFor = (s: Stop) => day.value?.warnings.find(w => w.place_id === s.place.id)?.message
const toMin = (hms: string) => { const [h, m] = hms.split(':').map(Number); return h * 60 + m }
const gapMin = (a: string, b: string) => toMin(b) - toMin(a)
// The answers from the plan page, shown under the title and sent back when they change them.
const trip = computed(() => {
  const i = plan.value?.intake
  if (!i) return null
  const days = plan.value!.days.length
  const people = i.group === 'solo' ? 1 : i.group === 'duo' ? 2 : i.group_count ?? 0
  return {
    title: `${days === 1 ? '1 day' : `${days} days`} from ${i.stay.label}`,
    dates: days === 1 ? dayLabel(i.start_date) : `${dayLabel(i.start_date)} to ${dayLabel(i.end_date)}`,
    start: clock(i.start_time),
    perDay: i.budget_php && people ? Math.round(i.budget_php / (people * days)) : null,
    people: people === 1 ? '1 person' : `${people} people`,
    places: i.places_per_day ? `${i.places_per_day} ${i.places_per_day === 1 ? 'place' : 'places'} a day` : null,
    meals: i.include_meals ? 'Places to eat included' : 'No places to eat',
    budget: i.budget_php ? `${pesos(i.budget_php)} total budget` : null,
    edit: {
      path: '/plan',
      query: Object.fromEntries(Object.entries({
        stay: i.stay.label,
        start: i.start_date,
        end: i.end_date !== i.start_date ? i.end_date : '',
        time: i.start_time.slice(0, 5),
        group: i.group,
        people: i.group_count ? String(i.group_count) : '',
        budget: i.budget_php ? String(i.budget_php) : '',
        places: i.places_per_day ? String(i.places_per_day) : '',
        food: i.include_meals ? '' : 'no',
        needs: i.access_needs.join(','),
        interests: i.interests_text ?? '',
      }).filter(([, v]) => v)),
    },
  }
})
// Places to add, loaded again when the day or the plan changes.
const recommendations = ref<SwapCandidate[]>([])
const choicesLoading = ref(false)
async function loadRecommendations() {
  if (!plan.value) return
  choicesLoading.value = true
  const want = `${plan.value.version}:${dayIndex.value}`
  try {
    const got = await api.dayRecommendations(plan.value.id, dayIndex.value)
    if (want === `${plan.value?.version}:${dayIndex.value}`) recommendations.value = got
  } catch {
    recommendations.value = [] // the plan still works; only the suggestions are missing
  } finally {
    choicesLoading.value = false
  }
}
watch(() => [plan.value?.version, dayIndex.value], loadRecommendations)
const dayFull = computed(() => (day.value?.stops.length ?? 0) >= MAX_STOPS_PER_DAY)

const PART_LABEL = { morning: 'Morning', afternoon: 'Afternoon', evening: 'Evening' } as const
const partStarts = (i: number) =>
  i === 0 || partOfDay(day.value!.stops[i - 1].arrive) !== partOfDay(day.value!.stops[i].arrive)

// Cost guide: meals and hot springs only. Open places and malls are not priced.
const peopleCount = computed(() => {
  const i = plan.value?.intake
  return !i ? 1 : i.group === 'solo' ? 1 : i.group === 'duo' ? 2 : i.group_count ?? 1
})
const tier = computed(() => plan.value?.intake.budget ?? 'mid')
const costOf = (s: Stop) => stopCost(s, tier.value)?.text
const estimate = computed(() => day.value ? dayCost(day.value.stops, tier.value, peopleCount.value) : null)
const overBudget = computed(() => {
  const per = trip.value?.perDay
  return !!(per && estimate.value && estimate.value.total > per * peopleCount.value)
})

// A long free stretch right before a meal can take one more place. We offer the closest one.
const gapPick = computed(() =>
  recommendations.value.length ? [...recommendations.value].sort((a, b) => a.delta_travel_s - b.delta_travel_s)[0] : null)
const gapOffer = (i: number) => {
  const stops = day.value!.stops
  return !dayFull.value && !!gapPick.value && i > 0 && isEatStop(stops[i]) && !isEatStop(stops[i - 1])
    && partOfDay(stops[i - 1].depart) !== 'morning'
}
const gapPart = (i: number) => partOfDay(day.value!.stops[i - 1].depart)

function pickStop(order: number | null) {
  selected.value = selected.value === order ? null : order
  if (mapOpen.value && order !== null) { mapOpen.value = false }
  if (order !== null) document.getElementById(`stop-${order}`)?.scrollIntoView({ block: 'center', behavior: 'smooth' })
}
watch(dayIndex, () => (selected.value = null))

const dayWarnings = computed(() => day.value?.warnings.filter(w => !w.place_id) ?? [])

let toastTimer: ReturnType<typeof setTimeout> | undefined
function say(message: string, undo?: () => void) {
  toast.value = message
  toastUndo.value = undo ?? null
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toast.value = ''; toastUndo.value = null }, undo ? 9000 : 4000)
}

// Add and remove both rebuild the day, so the times and drives stay right.
async function edit(run: (p: Itinerary) => Promise<Itinerary>, done: string) {
  if (!plan.value) return
  applying.value = true
  try {
    plan.value = await run(plan.value)
    say(done)
  } catch (e) {
    say(e instanceof TripApiError && e.code === 'stale_version'
      ? 'This plan changed in another tab. Reload to see the latest.'
      : e instanceof TripApiError && e.message ? e.message : 'That change didn’t save. Your plan is unchanged.')
  } finally {
    applying.value = false
  }
}

const addPlace = (c: SwapCandidate, part: 'morning' | 'afternoon' | 'evening') =>
  edit(p => api.addStop(p.id, { version: p.version, day_index: dayIndex.value, new_place_id: c.place.id, part }),
    `Added ${c.place.name} to your ${part}.`)

// Remove can be undone: the place goes back to the same part of the day (lunch or dinner stay meals).
function putBack(s: Stop) {
  const part = partOfDay(s.arrive)
  const meal = /^dinner\b/i.test(s.reason) ? 'dinner' : /^lunch\b/i.test(s.reason) ? 'lunch' : undefined
  return edit(p => api.addStop(p.id, { version: p.version, day_index: dayIndex.value, new_place_id: s.place.id, part, meal }),
    `Put ${s.place.name} back.`)
}
async function removePlace(s: Stop) {
  const before = plan.value?.version
  selected.value = null
  await edit(p => api.removeStop(p.id, { version: p.version, day_index: dayIndex.value, stop_order: s.order }),
    `Removed ${s.place.name}.`)
  if (plan.value && plan.value.version !== before) say(`Removed ${s.place.name}.`, () => putBack(s))
}

// Plans save themselves; the link is the way back to one.
async function share() {
  const url = window.location.href
  try {
    if (navigator.share) { await navigator.share({ title: trip.value?.title, url }); return }
    await navigator.clipboard.writeText(url)
    say('Link copied. Anyone with it can see this plan.')
  } catch {
    say('Copy the link from your browser’s address bar.')
  }
}
const print = () => window.print()
</script>

<template>
  <div class="mx-auto max-w-page px-4 sm:px-6 pt-8 pb-20">
    <StateBlock v-if="state === 'loading'" kind="loading" title="Loading your plan" />
    <StateBlock v-else-if="state === 'missing'" kind="empty" title="This plan doesn't exist" body="The link may be old. Start a new plan in under a minute." action-label="Plan a trip" @action="navigateTo('/plan')" />
    <StateBlock v-else-if="state === 'error'" kind="error" title="Your plan didn't load" body="Check your connection, then try again." action-label="Try again" @action="load" />

    <template v-else-if="plan && day">
      <header class="-mx-4 sm:-mx-6 -mt-8 px-4 sm:px-6 pt-6 pb-7 bg-lake-soft/60 [box-shadow:0_0_0_100vmax_rgb(var(--lake-soft)/0.6)] [clip-path:inset(0_-100vmax)] print:shadow-none print:bg-transparent">
        <div class="mx-auto max-w-page">
          <div class="flex flex-wrap items-center gap-x-3 gap-y-2 print:hidden">
            <NuxtLink :to="trip!.edit" class="inline-flex items-center gap-1.5 rounded-pill border border-line bg-surface px-4 min-h-[40px] text-sm font-semibold hover:border-ink/40"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" aria-hidden="true"><path d="M19 12H5M11 6l-6 6 6 6" /></svg>Edit answers</NuxtLink>
            <p class="text-sm text-muted">Saved automatically. Bookmark this link to come back.</p>
            <div class="ml-auto flex gap-2">
              <button type="button" class="inline-flex items-center gap-1.5 rounded-pill border border-line bg-surface px-4 min-h-[40px] text-sm font-semibold hover:border-ink/40" @click="share">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" aria-hidden="true"><path d="M4 12v7a1 1 0 001 1h14a1 1 0 001-1v-7M16 6l-4-4-4 4M12 2v13" /></svg>Share
              </button>
              <button type="button" class="inline-flex items-center gap-1.5 rounded-pill border border-line bg-surface px-4 min-h-[40px] text-sm font-semibold hover:border-ink/40" @click="print">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" aria-hidden="true"><path d="M6 9V3h12v6M6 18H4a1 1 0 01-1-1v-6a1 1 0 011-1h16a1 1 0 011 1v6a1 1 0 01-1 1h-2M6 14h12v7H6z" /></svg>Print
              </button>
            </div>
          </div>
          <h1 class="mt-5 text-[32px] sm:text-[44px] font-extrabold tracking-[-0.025em] leading-[1.08]">{{ trip!.title }}</h1>
          <ul class="mt-4 flex flex-wrap gap-2 text-sm" aria-label="Your answers">
            <li class="rounded-pill bg-surface border border-line px-3.5 py-1.5 font-semibold">{{ trip!.dates }}</li>
            <li class="rounded-pill bg-surface border border-line px-3.5 py-1.5">Start {{ trip!.start }}</li>
            <li class="rounded-pill bg-surface border border-line px-3.5 py-1.5">{{ trip!.people }}</li>
            <li v-if="trip!.places" class="rounded-pill bg-surface border border-line px-3.5 py-1.5">{{ trip!.places }}</li>
            <li class="rounded-pill bg-surface border border-line px-3.5 py-1.5">{{ trip!.meals }}</li>
            <li v-if="trip!.budget" class="rounded-pill bg-surface border border-line px-3.5 py-1.5">{{ trip!.budget }}<template v-if="trip!.perDay">, about {{ pesos(trip!.perDay) }} per person a day</template></li>
          </ul>
        </div>
      </header>

      <div role="tablist" aria-label="Days" class="mt-6 flex gap-2 overflow-x-auto pb-1 print:hidden">
        <button v-for="(d, i) in plan.days" :key="d.date" role="tab" type="button" :aria-selected="i === dayIndex"
          class="shrink-0 rounded-[14px] border px-5 py-2.5 text-left transition-colors"
          :class="i === dayIndex ? 'border-lake bg-lake text-surface shadow-lift' : 'border-line bg-surface hover:border-ink/40 hover:bg-soft'"
          @click="dayIndex = i">
          <span class="block font-bold">Day {{ i + 1 }}</span>
          <span class="block text-xs" :class="i === dayIndex ? 'opacity-90' : 'text-muted'">{{ dayLabel(d.date) }}, {{ stopsLabel(d.stops) }}</span>
        </button>
      </div>

      <div class="mt-6 lg:grid lg:grid-cols-[minmax(0,1fr)_minmax(0,26rem)] lg:gap-10">
        <section role="tabpanel" :aria-label="`Day ${dayIndex + 1}`">
          <dl class="grid grid-cols-2 sm:grid-cols-4 gap-px overflow-hidden rounded-card border border-line bg-line shadow-sm" aria-label="This day at a glance">
            <div class="bg-surface px-4 py-3.5"><dt class="text-xs text-muted">Stops</dt><dd class="mt-0.5 text-lg font-extrabold tracking-tight">{{ stopsLabel(day.stops) }}</dd></div>
            <div class="bg-surface px-4 py-3.5"><dt class="text-xs text-muted">Driving</dt><dd class="mt-0.5 text-lg font-extrabold tracking-tight">{{ minutes(day.total_travel_s) }}</dd></div>
            <div class="bg-surface px-4 py-3.5"><dt class="text-xs text-muted">Day ends</dt><dd class="mt-0.5 text-lg font-extrabold tracking-tight">{{ day.stops.length ? clock(day.stops[day.stops.length - 1].depart) : 'None' }}</dd></div>
            <div class="px-4 py-3.5" :class="overBudget ? 'bg-mango/15' : 'bg-surface'">
              <dt class="text-xs text-muted">Food and entry<template v-if="peopleCount > 1">, {{ peopleCount }} people</template></dt>
              <dd class="mt-0.5 text-lg font-extrabold tracking-tight">{{ estimate && estimate.count ? `${estimate.from ? 'from ' : ''}${pesos(estimate.total)}` : 'Free' }}</dd>
            </div>
          </dl>
          <div v-if="dayWarnings.length || (estimate && estimate.count)" class="mt-3 rounded-card border border-mango/40 bg-mango/10 px-4 py-3 text-sm">
            <p class="flex items-center gap-2 font-bold"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" aria-hidden="true"><circle cx="12" cy="12" r="9" /><path d="M12 8v5M12 16.5v.01" /></svg>Good to know</p>
            <ul class="mt-1.5 list-disc pl-5 space-y-1 text-muted marker:text-mango">
              <li v-for="w in dayWarnings" :key="w.code">{{ w.message }}</li>
              <li v-if="estimate && estimate.count">
                A rough guide: meals use Calamba averages<template v-if="day.stops.some(s => s.place.category === 'hot_springs')">, and hot springs usually start at {{ pesos(800) }} per person</template>. Open places, parks and malls are not priced. Check prices before you go.
                <template v-if="overBudget"> This is above your budget of about {{ pesos(trip!.perDay!) }} per person a day.</template>
              </li>
            </ul>
          </div>

      <div v-if="!day.stops.length" class="mt-6">
            <StateBlock kind="empty" title="A rest day" body="Nothing planned. Swap in a place from another day, or enjoy the pool." />
          </div>

          <ol v-else class="ribbon relative mt-6">
            <li class="relative pl-12 pb-1">
              <span class="absolute left-[7px] top-1 h-[22px] w-[22px] rounded-[6px] bg-lake ring-4 ring-bg" aria-hidden="true" />
              <p class="font-semibold">Start at {{ plan.intake.stay.label }} <span class="font-normal text-muted">at {{ trip!.start }}</span></p>
            </li>
            <template v-for="(s, i) in day.stops" :key="s.place.id + s.order">
              <li v-if="partStarts(i)" class="relative pl-12 pt-4 pb-1">
                <h2 class="text-lg font-extrabold tracking-tight">{{ PART_LABEL[partOfDay(s.arrive)] }}</h2>
              </li>
              <li><LegRow :leg="day.legs[i]" /></li>
              <li v-if="i > 0 && gapMin(day.stops[i - 1].depart, s.arrive) - day.legs[i].duration_s / 60 >= 90" class="relative pl-12 py-1">
                <p class="rounded-[12px] border border-dashed border-line bg-soft px-4 py-2.5 text-sm text-muted">
                  <span class="font-semibold text-ink">Free time, about {{ minutes((gapMin(day.stops[i - 1].depart, s.arrive) - day.legs[i].duration_s / 60) * 60) }}.</span>
                  Rest at your stay or take it slow before the next stop.
                </p>
                <button v-if="gapOffer(i)" type="button" :disabled="applying" class="mt-2 inline-flex items-center gap-1.5 rounded-pill bg-lake px-4 min-h-[40px] text-sm font-semibold text-surface hover:opacity-90 disabled:opacity-50 print:hidden"
                  @click="addPlace(gapPick!, gapPart(i))">
                  Add {{ gapPick!.place.name }} to your {{ gapPart(i) }}
                </button>
              </li>
              <li><StopCard :stop="s" :note="noteFor(s)" :busy="applying" :selected="selected === s.order" :cost="costOf(s)" @select="pickStop(s.order)" @remove="removePlace(s)" /></li>
            </template>
            <li><LegRow :leg="day.legs[day.legs.length - 1]" /></li>
            <li class="relative pl-12">
              <span class="absolute left-[7px] top-1 h-[22px] w-[22px] rounded-[6px] bg-lake ring-4 ring-bg" aria-hidden="true" />
              <p class="font-semibold">Back to {{ plan.intake.stay.label }}</p>
            </li>
          </ol>
          <TripRecommendations class="print:hidden" :items="recommendations" :loading="choicesLoading" :applying="applying" :full="dayFull"
            @add="addPlace" />
        </section>

        <div class="fixed inset-0 z-[1250] bg-bg transition-transform duration-200 lg:static lg:z-auto lg:translate-y-0 lg:h-[calc(100dvh-7rem)] lg:sticky lg:top-20 lg:overflow-hidden lg:rounded-card lg:border lg:border-line lg:shadow-lift print:hidden"
          :class="mapOpen ? 'translate-y-0' : 'translate-y-full invisible lg:visible'">
          <button type="button" class="absolute right-3 top-3 z-[1000] inline-flex items-center gap-1.5 rounded-pill bg-surface border border-line px-4 min-h-[44px] text-sm font-semibold shadow-lift lg:hidden" @click="mapOpen = false">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18" /></svg>Close map
          </button>
          <RouteMap :day="day" :stay="plan.stay_coords" :selected="selected" @select="pickStop" />
        </div>
      </div>

      <button type="button" class="fixed bottom-5 left-1/2 -translate-x-1/2 z-[1100] inline-flex items-center gap-2 rounded-pill bg-lake text-surface px-6 min-h-[48px] font-semibold shadow-lift lg:hidden print:hidden" @click="mapOpen = true">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" aria-hidden="true"><path d="M9 4L3 6v14l6-2 6 2 6-2V4l-6 2-6-2zM9 4v14M15 6v14" /></svg>Show map
      </button>
      <p v-if="toast" role="status" class="fixed bottom-24 lg:bottom-5 left-1/2 -translate-x-1/2 z-[1200] flex items-center gap-4 rounded-pill bg-ink text-bg pl-5 pr-3 py-2.5 text-sm font-medium shadow-lift print:hidden">
        <span>{{ toast }}</span>
        <button v-if="toastUndo" type="button" class="rounded-pill bg-bg/15 px-3 min-h-[32px] font-bold hover:bg-bg/25" @click="toastUndo?.(); toastUndo = null">Undo</button>
      </p>
    </template>
  </div>
</template>

<style scoped>
/* The route ribbon: one mango line from leaving the stay to coming back. */
.ribbon::before {
  content: '';
  position: absolute;
  left: 16px;
  top: 14px;
  bottom: 14px;
  width: 4px;
  border-radius: 4px;
  background: rgb(var(--mango));
}
</style>
<style>
.leaflet-control-attribution.leaflet-control-attribution { font-size: 11px; }
</style>
