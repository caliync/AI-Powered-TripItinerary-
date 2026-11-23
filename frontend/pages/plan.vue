<script setup lang="ts">
// The full set of questions. Answers from the home page planner arrive in the query string
// and are filled in here.
import type { AccessNeed, GroupSize } from '~/types/itinerary'
import { INTEREST_LABELS } from '~/data/interestWords'
import { TIER_LABEL } from '~/composables/useIntakeForm'
import { MAX_PLACES, START_TIMES } from '~/data/tripOptions'

useHead({ title: 'Plan a trip, LakbayWise' })
const { form, errors, touched, isValid, tripDays, perPersonDay, budgetTier, interests, today, toIntake } = useIntakeForm()
const query = useRoute().query
const str = (v: unknown) => (typeof v === 'string' ? v : '')
form.stayLabel = str(query.stay)
const lat = Number(str(query.lat)), lng = Number(str(query.lng))
if (form.stayLabel && str(query.lat) && str(query.lng) && Number.isFinite(lat) && Number.isFinite(lng)) form.stayCoords = { lat, lng }
form.startDate = str(query.start) >= today ? str(query.start) : ''
form.endDate = form.startDate && str(query.end) >= form.startDate ? str(query.end) : ''
if (['solo', 'duo', 'group'].includes(str(query.group))) form.group = str(query.group) as GroupSize
// The rest come back from "Change trip details" on the trip page.
const groupCount = Number(str(query.people))
if (groupCount >= 3 && groupCount <= 30) form.groupCount = groupCount
if (START_TIMES.some(t => t.value === str(query.time))) form.startTime = str(query.time)
const budget = Number(str(query.budget))
if (budget > 0) form.budgetText = budget.toLocaleString('en-US')
const places = Number(str(query.places))
if (places >= 1 && places <= MAX_PLACES) form.placesPerDay = places
if (str(query.food) === 'no') form.includeFood = false
form.interestsText = str(query.interests)
form.accessNeeds = str(query.needs).split(',').filter((n): n is AccessNeed =>
  ['wheelchair', 'minimal_walking', 'sensory_friendly'].includes(n))
const api = useTripApi()
const submitting = ref(false)
const submitError = ref('')

// Whole pesos, shown with thousands commas as the traveller types (10000 becomes 10,000).
function onBudgetInput(e: Event) {
  const el = e.target as HTMLInputElement
  const caret = el.selectionStart ?? el.value.length
  const digitsBeforeCaret = el.value.slice(0, caret).replace(/\D/g, '').replace(/^0+/, '').length
  const digits = el.value.replace(/\D/g, '').replace(/^0+/, '').slice(0, 8)
  const shown = digits ? Number(digits).toLocaleString('en-US') : ''
  form.budgetText = shown
  el.value = shown
  let pos = 0
  for (let seen = 0; pos < shown.length && seen < digitsBeforeCaret; pos++) if (/\d/.test(shown[pos])) seen++
  el.setSelectionRange(pos, pos)
}

// Backspace or Delete next to a comma removes the digit beside it, not just the comma.
function onBudgetKeydown(e: KeyboardEvent) {
  const el = e.target as HTMLInputElement
  const at = el.selectionStart ?? 0
  if (at !== el.selectionEnd) return
  if (e.key === 'Backspace' && el.value[at - 1] === ',') el.setSelectionRange(at - 1, at - 1)
  if (e.key === 'Delete' && el.value[at] === ',') el.setSelectionRange(at + 1, at + 1)
}

const groups = [
  { value: 'solo', label: 'Just me' },
  { value: 'duo', label: 'Two of us' },
  { value: 'group', label: 'A group', hint: '3 to 30 people' },
]
const needs: Array<{ value: AccessNeed; label: string }> = [
  { value: 'wheelchair', label: 'Wheelchair user' },
  { value: 'minimal_walking', label: 'Minimal walking' },
  { value: 'sensory_friendly', label: 'Quiet, low-sensory places' },
]

const shown = (k: keyof typeof errors.value) => (touched.value ? errors.value[k] : undefined)
const startLabel = computed(() => START_TIMES.find(t => t.value === form.startTime)?.label ?? form.startTime)
const placesHint = computed(() => {
  const n = form.placesPerDay
  const pace = n <= 2 ? 'A slow, easy day' : n <= 4 ? 'A relaxed day' : 'A full day'
  return `${pace}: ${n === 1 ? '1 place' : `${n} places`}${form.includeFood ? ', plus meals' : ''}.`
})
const missing = computed(() => [
  errors.value.stay && 'where you stay', errors.value.dates && 'your dates',
  errors.value.group && 'who’s going', errors.value.budget && 'your budget',
].filter(Boolean).join(', '))
const dayCount = computed(() => (tripDays.value === 1 ? '1 day' : `${tripDays.value} days`))

async function submit() {
  touched.value = true
  submitError.value = ''
  if (!isValid.value) return
  submitting.value = true
  try {
    const it = await api.generate(toIntake())
    await navigateTo(`/trip/${it.id}`)
  } catch (e) {
    // Messages from the API (e.g. a stay we can't find) are written for the traveller.
    submitError.value = (e instanceof TripApiError && e.message)
      || (import.meta.dev
        ? 'The planner did not answer. Is the backend running on port 8000? In the backend folder: uvicorn app.api:app --reload'
        : 'We could not build your plan. Check your connection and try again.')
  } finally {
    submitting.value = false
  }
}

const field = 'mt-1 w-full rounded-[12px] border border-line bg-surface px-4 py-3.5 shadow-sm focus:border-lake focus:ring-2 focus:ring-lake/25 outline-none'
</script>

<template>
  <div class="mx-auto max-w-page px-4 sm:px-6 pt-10 pb-20 lg:grid lg:grid-cols-[1fr_22rem] lg:gap-16">
    <form novalidate @submit.prevent="submit">
      <h1 class="text-[34px] sm:text-[44px] font-extrabold tracking-[-0.02em] leading-[1.08] max-w-[20ch]">
        Plan your trip
      </h1>
      <p class="mt-3 text-lg text-muted max-w-[52ch]">
        Five short steps. We group nearby places into one area per day and put them in an order that keeps you off the highway.
      </p>

      <div class="mt-8">
        <IntakeSection :step="1" title="Where are you staying, and when?" :error="shown('stay') || shown('dates')">
          <StayInput v-model="form.stayLabel" v-model:coords="form.stayCoords" :invalid="!!shown('stay')" />
          <div class="mt-4 grid grid-cols-2 sm:grid-cols-3 gap-3 max-w-xl">
            <label class="text-sm font-medium">Arrive
              <input v-model="form.startDate" type="date" :min="today" :class="field" class="px-3 py-3">
            </label>
            <label class="text-sm font-medium">Leave <span class="font-normal text-muted">optional</span>
              <input v-model="form.endDate" type="date" :min="form.startDate || today" :class="field" class="px-3 py-3">
            </label>
            <label class="text-sm font-medium">Start each day at
              <select v-model="form.startTime" :class="field" class="px-3 py-3">
                <option v-for="t in START_TIMES" :key="t.value" :value="t.value">{{ t.label }}</option>
              </select>
            </label>
          </div>
          <p v-if="form.startDate" class="mt-2 text-sm text-muted">
            {{ form.endDate ? `A ${dayCount} trip` : 'No leaving date, so we’ll plan 1 day' }}, leaving your stay at {{ startLabel }}{{ form.endDate && tripDays > 1 ? ' each day' : '' }}.
          </p>
        </IntakeSection>

        <IntakeSection :step="2" title="Who's going?" :error="shown('group')">
          <div class="grid sm:grid-cols-3 gap-3">
            <ChoiceCard v-for="g in groups" :key="g.value" v-model="form.group" name="group" v-bind="g" />
          </div>
          <label v-if="form.group === 'group'" class="mt-3 inline-flex items-center gap-3 text-sm font-medium">
            How many people?
            <input v-model.number="form.groupCount" type="number" min="3" max="30" class="w-20 rounded-[12px] border border-line bg-surface px-3 py-2 focus:border-lake focus:ring-2 focus:ring-lake/25 outline-none">
          </label>
        </IntakeSection>

        <IntakeSection :step="3" title="What's your budget, and how many places do you want to stop by?" :error="shown('budget')"
          hint="Your budget is the total for the whole trip, for everyone, in pesos.">
          <label class="block max-w-xs text-sm font-medium" for="budget">Total budget</label>
          <div class="relative max-w-xs">
            <span class="pointer-events-none absolute left-4 top-1/2 mt-0.5 -translate-y-1/2 font-semibold text-muted" aria-hidden="true">₱</span>
            <input id="budget" :value="form.budgetText" type="text" inputmode="numeric" autocomplete="off" placeholder="e.g. 10,000"
              :class="field" class="pl-9" @input="onBudgetInput" @keydown="onBudgetKeydown">
          </div>
          <p v-if="perPersonDay && budgetTier" class="mt-2 text-sm text-muted">
            About {{ pesos(perPersonDay) }} per person per day, so we’ll suggest {{ TIER_LABEL[budgetTier] }} places.
          </p>

          <fieldset class="mt-6">
            <legend class="text-sm font-medium">Places to stop by each day</legend>
            <div class="mt-1 flex flex-wrap gap-2">
              <label v-for="n in MAX_PLACES" :key="n"
                class="relative grid place-items-center h-12 w-12 rounded-[12px] border cursor-pointer bg-surface font-semibold transition-shadow"
                :class="form.placesPerDay === n ? 'border-lake ring-1 ring-lake bg-lake-soft/60 text-lake' : 'border-line hover:border-ink/40 hover:shadow-sm'">
                <input v-model="form.placesPerDay" type="radio" name="places" :value="n" class="sr-only peer">
                {{ n }}
                <span class="pointer-events-none absolute inset-0 rounded-[12px] peer-focus-visible:outline peer-focus-visible:outline-3 peer-focus-visible:outline-mango" aria-hidden="true" />
              </label>
            </div>
            <p class="mt-2 text-sm text-muted">{{ placesHint }}</p>
          </fieldset>

          <button type="button" role="switch" :aria-checked="form.includeFood"
            class="mt-6 flex w-full max-w-xl items-center gap-4 rounded-[14px] border border-line bg-surface px-4 py-3.5 text-left hover:border-ink/40"
            @click="form.includeFood = !form.includeFood">
            <span class="relative h-7 w-12 shrink-0 rounded-pill transition-colors" :class="form.includeFood ? 'bg-lake' : 'bg-line'" aria-hidden="true">
              <span class="absolute top-1 h-5 w-5 rounded-full bg-surface shadow transition-all" :class="form.includeFood ? 'left-6' : 'left-1'" />
            </span>
            <span>
              <span class="block font-semibold">Include places to eat</span>
              <span class="block text-sm text-muted">{{ form.includeFood ? 'We’ll add lunch and dinner stops near your route.' : 'No meal stops. Good if you’re bringing your own food.' }}</span>
            </span>
          </button>
        </IntakeSection>

        <IntakeSection :step="4" title="Anything we should plan around?" optional
          hint="We only suggest places that suit these needs. Places we haven't checked yet are shown with a note.">
          <div class="flex flex-wrap gap-2">
            <ToggleChip v-for="n in needs" :key="n.value" v-model="form.accessNeeds" v-bind="n" />
          </div>
        </IntakeSection>

        <IntakeSection :step="5" title="What places are you thinking about?" optional
          hint="Type anything you like. Leave it blank for a mix.">
          <label class="sr-only" for="interests">Places you're thinking about</label>
          <textarea id="interests" v-model="form.interestsText" rows="2" maxlength="300"
            placeholder="Waterfalls, hot springs & resorts, cafés, local food…" :class="field" class="resize-none" />
          <div v-if="interests.length" class="mt-3 flex flex-wrap items-center gap-2" aria-live="polite">
            <span class="text-sm text-muted">We’ll look for:</span>
            <span v-for="i in interests" :key="i" class="rounded-pill bg-lake-soft px-3 py-1 text-sm font-semibold text-lake">{{ INTEREST_LABELS[i] }}</span>
          </div>
          <p v-else-if="form.interestsText.trim()" class="mt-2 text-sm text-muted" aria-live="polite">
            We didn’t recognise those yet, so we’ll plan a mix.
          </p>
        </IntakeSection>
      </div>

      <div class="lg:hidden mt-4">
        <button type="submit" :disabled="submitting" class="w-full rounded-[14px] bg-lake text-surface font-bold min-h-[52px] disabled:opacity-60">
          {{ submitting ? 'Building your plan…' : 'Plan my trip' }}
        </button>
        <p v-if="submitError" role="alert" class="mt-2 text-sm text-danger">{{ submitError }}</p>
      </div>
    </form>

    <aside class="hidden lg:block">
      <div class="sticky top-24 rounded-[20px] border border-line bg-surface p-6 shadow-lift">
        <p class="text-lg font-bold">Your trip</p>
        <dl class="mt-3 space-y-2 text-sm">
          <div class="flex justify-between gap-3"><dt class="text-muted">Base</dt><dd class="text-right truncate">{{ form.stayLabel || 'Not set' }}</dd></div>
          <div class="flex justify-between"><dt class="text-muted">Days</dt><dd>{{ tripDays || '–' }}</dd></div>
          <div class="flex justify-between"><dt class="text-muted">Start</dt><dd>{{ startLabel }}</dd></div>
          <div class="flex justify-between"><dt class="text-muted">Budget</dt><dd class="first-letter:uppercase">{{ budgetTier ? TIER_LABEL[budgetTier] : '–' }}</dd></div>
          <div class="flex justify-between"><dt class="text-muted">Places a day</dt><dd>{{ form.placesPerDay }}</dd></div>
          <div class="flex justify-between"><dt class="text-muted">Meals</dt><dd>{{ form.includeFood ? 'Included' : 'Bringing own' }}</dd></div>
          <div class="flex justify-between"><dt class="text-muted">Needs</dt><dd>{{ form.accessNeeds.length || 'None' }}</dd></div>
          <div class="flex justify-between"><dt class="text-muted">Interests</dt><dd>{{ interests.length || 'A mix' }}</dd></div>
        </dl>
        <button type="button" :disabled="submitting" class="mt-6 w-full rounded-[14px] bg-lake hover:bg-lake-deep text-surface font-bold min-h-[52px] disabled:opacity-60" @click="submit">
          {{ submitting ? 'Building your plan…' : 'Plan my trip' }}
        </button>
        <p v-if="touched && !isValid" class="mt-2 text-sm text-danger">Finish steps 1 to 3 first: {{ missing }}.</p>
        <p v-if="submitError" role="alert" class="mt-2 text-sm text-danger">{{ submitError }}</p>
        <NuxtLink to="/trip/demo" class="mt-4 block text-center text-sm underline text-muted">See a sample plan</NuxtLink>
      </div>
    </aside>
  </div>
</template>
