<script setup lang="ts">
import type { LatLng } from '~/types/itinerary'
// Alli's photo hero with the planner form under it. The form hands the first answers
// to /plan, where the rest of the questions are asked.
const today = todayInManila()
const q = reactive({ stay: '', start: '', end: '', group: '' })
const stayCoords = ref<LatLng | null>(null)
const { options, open, active, onInput, pick, onKey, onBlur, onFocus } = useStaySuggest(toRef(q, 'stay'), stayCoords)

// Date fields read "Add date" until used, then show the browser's picker.
const focused = ref<'' | 'start' | 'end'>('')
const kind = (k: 'start' | 'end') => (q[k] || focused.value === k ? 'date' : 'text')
function openPicker(e: FocusEvent, k: 'start' | 'end') {
  focused.value = k
  nextTick(() => { try { (e.target as HTMLInputElement).showPicker?.() } catch { /* needs a user gesture */ } })
}

function go() {
  // Every box is optional here; whatever was filled in is carried over to the plan page.
  const query: Record<string, string> = Object.fromEntries(Object.entries(q).filter(([, v]) => v))
  if (query.stay && stayCoords.value) {
    query.lat = String(stayCoords.value.lat)
    query.lng = String(stayCoords.value.lng)
  }
  navigateTo({ path: '/plan', query })
}
</script>

<template>
  <section id="top" class="hero">
    <img class="hero-photo" src="/img/hero-laguna.jpg" alt="A traveler standing beside a red vehicle on a quiet tree-lined road">
    <div class="hero-shade" />
    <div class="hero-copy">
      <div class="hero-title">
        <h1>PLAN A DAY IN LAGUNA</h1>
        <span class="title-rule" aria-hidden="true"><i /></span>
      </div>
      <p>Tell us where you’re staying and what you enjoy. We’ll plan the rest of your day.</p>
    </div>
  </section>

  <section id="plan" class="planner" aria-label="Start a trip plan">
    <form role="search" @submit.prevent="go">
      <label class="field stay-field">
        <span>Where you’re staying</span>
        <input v-model="q.stay" name="stay" placeholder="Hotel, resort or address" autocomplete="off"
          role="combobox" aria-autocomplete="list" aria-controls="home-stay-options" :aria-expanded="open"
          :aria-activedescendant="active >= 0 ? `home-stay-${active}` : undefined"
          @input="onInput" @keydown="onKey" @blur="onBlur" @focus="onFocus">
        <ul v-show="open" id="home-stay-options" class="stay-options" role="listbox" aria-label="Places to stay">
          <li v-for="(s, i) in options" :id="`home-stay-${i}`" :key="s.name + i" role="option"
            :aria-selected="i === active" :class="{ active: i === active }" @mousedown.prevent="pick(s)">
            <strong>{{ s.name }}</strong><em>{{ STAY_KIND[s.kind] ?? 'Place' }}</em>
          </li>
        </ul>
      </label>
      <label class="field">
        <span>Arrive</span>
        <input v-model="q.start" name="arrival" :type="kind('start')" :min="today" placeholder="Add date"
          @focus="openPicker($event, 'start')" @blur="focused = ''">
      </label>
      <label class="field">
        <span>Leave</span>
        <input v-model="q.end" name="departure" :type="kind('end')" :min="q.start || today" placeholder="Add date"
          @focus="openPicker($event, 'end')" @blur="focused = ''">
      </label>
      <label class="field travelers-field">
        <span>Who’s going</span>
        <select v-model="q.group" name="group">
          <option value="" disabled>Add travelers</option>
          <option value="solo">Just me</option>
          <option value="duo">Two of us</option>
          <option value="group">A group of 3 or more</option>
        </select>
        <i class="field-chevron"><LwIcon name="chevron" /></i>
      </label>
      <button class="plan-button" type="submit"><LwIcon name="search" />Plan my trip</button>
    </form>
    <p class="form-status" aria-live="polite" />
  </section>
</template>
