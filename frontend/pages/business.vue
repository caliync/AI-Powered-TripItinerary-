<script setup lang="ts">
// Owner form. Every entry is reviewed by a person before it appears in plans.
import type { AccessStatus, BusinessSubmission, LatLng, Place } from '~/types/itinerary'

const api = useTripApi()
const form = reactive({
  name: '', category: '' as Place['category'] | '', pin: null as LatLng | null,
  hours: '', wheelchair: 'unknown' as AccessStatus, website: '', email: '',
})
const touched = ref(false)
const state = ref<'idle' | 'sending' | 'sent' | 'error'>('idle')
const serverMessage = ref('')

const categories: Array<{ value: Place['category']; label: string }> = [
  { value: 'traditional_food', label: 'Filipino food' }, { value: 'seafood', label: 'Seafood' },
  { value: 'cafes', label: 'Café' }, { value: 'hot_springs', label: 'Hot spring or resort' },
  { value: 'farms', label: 'Farm' }, { value: 'parks', label: 'Park or nature' },
  { value: 'malls', label: 'Shop or market' }, { value: 'other', label: 'Something else' },
]
const access: Array<{ value: AccessStatus; label: string }> = [
  { value: 'yes', label: 'Yes, step-free throughout' }, { value: 'limited', label: 'Partly, e.g. entrance only' },
  { value: 'no', label: 'No' }, { value: 'unknown', label: 'Not sure' },
]

const errors = computed(() => {
  const e: Partial<Record<'name' | 'category' | 'pin' | 'email' | 'website', string>> = {}
  if (form.name.trim().length < 2) e.name = 'Enter your business name.'
  if (!form.category) e.category = 'Choose what kind of place it is.'
  if (!form.pin) e.pin = 'Click the map where your entrance is.'
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(form.email.trim())) e.email = 'Enter an email we can reach you at, like name@example.com.'
  if (form.website && !/^https?:\/\/\S+\.\S+/.test(form.website.trim())) e.website = 'Start the link with https://'
  return e
})
const err = (k: keyof typeof errors.value) => (touched.value ? errors.value[k] : undefined)

async function submit() {
  touched.value = true
  if (Object.keys(errors.value).length) return
  state.value = 'sending'
  const body: BusinessSubmission = {
    region: 'calamba', business_name: form.name.trim(), category: form.category as Place['category'], coords: form.pin!,
    opening_hours: form.hours.trim() || null, wheelchair: form.wheelchair, website: form.website.trim() || null, contact_email: form.email.trim(),
  }
  try {
    await api.submitBusiness(body)
    state.value = 'sent'
  } catch (e) {
    serverMessage.value = e instanceof TripApiError ? e.message : ''
    state.value = 'error'
  }
}
const input = 'mt-1 w-full rounded-[12px] border border-line bg-surface px-4 py-3.5 shadow-sm focus:border-lake focus:ring-2 focus:ring-lake/25 outline-none'
</script>

<template>
  <div class="mx-auto max-w-2xl px-4 sm:px-6 pt-10 pb-20">
    <div v-if="state === 'sent'" role="status" class="py-10">
      <h1 class="text-3xl font-extrabold tracking-[-0.02em]">Thanks. {{ form.name }} is with our team.</h1>
      <p class="mt-3 text-muted max-w-[52ch]">We check every new place by hand, usually within a few days, and email {{ form.email }} when it starts showing up in trip plans.</p>
      <NuxtLink to="/" class="mt-6 inline-flex items-center min-h-[48px] rounded-[14px] bg-lake text-surface font-bold px-6">Back to the planner</NuxtLink>
    </div>

    <form v-else novalidate @submit.prevent="submit">
      <h1 class="text-[34px] sm:text-[44px] font-extrabold tracking-[-0.02em] leading-[1.08]">Put your Calamba business on the map.</h1>
      <p class="mt-3 text-lg text-muted max-w-[56ch]">Small and family-run places are welcome. Listing is free, and travellers see your place when it fits their day.</p>

      <div class="mt-8 space-y-6">
        <label class="block font-medium">Business name
          <input v-model="form.name" type="text" autocomplete="organization" :class="input" :aria-invalid="!!err('name')">
          <span v-if="err('name')" class="mt-1 block text-sm text-danger">{{ err('name') }}</span>
        </label>

        <fieldset>
          <legend class="font-medium">What kind of place is it?</legend>
          <div class="mt-2 flex flex-wrap gap-2">
            <label v-for="c in categories" :key="c.value" class="relative inline-flex items-center rounded-pill border px-4 min-h-[44px] text-[15px] font-medium cursor-pointer bg-surface focus-within:outline focus-within:outline-3 focus-within:outline-mango"
              :class="form.category === c.value ? 'border-lake ring-1 ring-lake bg-lake-soft/60' : 'border-line hover:border-ink/40'">
              <input v-model="form.category" type="radio" name="category" :value="c.value" class="sr-only">{{ c.label }}
            </label>
          </div>
          <p v-if="err('category')" class="mt-1 text-sm text-danger">{{ err('category') }}</p>
        </fieldset>

        <div>
          <p class="font-medium">Where is it?</p>
          <p class="text-sm text-muted">Click your entrance on the map. Zoom in for accuracy.</p>
          <div class="mt-2"><PinPicker v-model="form.pin" /></div>
          <p v-if="form.pin" class="mt-1 text-sm text-muted tabular-nums">Pinned at {{ form.pin.lat }}, {{ form.pin.lng }}</p>
          <p v-if="err('pin')" class="mt-1 text-sm text-danger">{{ err('pin') }}</p>
        </div>

        <label class="block font-medium">Opening hours <span class="text-muted font-normal">(optional)</span>
          <input v-model="form.hours" type="text" placeholder="e.g. Mon to Sat 8 AM to 9 PM" :class="input">
        </label>

        <fieldset>
          <legend class="font-medium">Can a wheelchair user get in and around?</legend>
          <div class="mt-2 grid sm:grid-cols-2 gap-2">
            <label v-for="a in access" :key="a.value" class="flex items-center gap-2.5 rounded-[12px] border px-4 min-h-[48px] text-[15px] cursor-pointer bg-surface"
              :class="form.wheelchair === a.value ? 'border-lake ring-1 ring-lake bg-lake-soft/60' : 'border-line hover:border-ink/40'">
              <input v-model="form.wheelchair" type="radio" name="wheelchair" :value="a.value" class="accent-[rgb(var(--lake))]">{{ a.label }}
            </label>
          </div>
        </fieldset>

        <label class="block font-medium">Website or Facebook page <span class="text-muted font-normal">(optional)</span>
          <input v-model="form.website" type="url" placeholder="https://" :class="input" :aria-invalid="!!err('website')">
          <span v-if="err('website')" class="mt-1 block text-sm text-danger">{{ err('website') }}</span>
        </label>

        <label class="block font-medium">Your email
          <input v-model="form.email" type="email" autocomplete="email" :class="input" :aria-invalid="!!err('email')">
          <span class="mt-1 block text-sm text-muted font-normal">Only used to tell you when your listing is live. Never shown to travellers.</span>
          <span v-if="err('email')" class="mt-1 block text-sm text-danger">{{ err('email') }}</span>
        </label>
      </div>

      <button type="submit" :disabled="state === 'sending'" class="mt-8 w-full sm:w-auto rounded-[14px] bg-lake hover:bg-lake-deep text-surface font-bold px-8 min-h-[52px] disabled:opacity-60">
        {{ state === 'sending' ? 'Sending…' : 'Send for review' }}
      </button>
      <p v-if="state === 'error'" role="alert" class="mt-2 text-sm text-danger">{{ serverMessage || "Your details didn't send. Check your connection and press Send for review again." }}</p>
    </form>
  </div>
</template>
