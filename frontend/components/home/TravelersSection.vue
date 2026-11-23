<script setup lang="ts">
// Travelers: what the planner does, a sample day card and the kinds of places we plan around.
import { placeTypes, sampleDay, travelers } from '~/data/landing'
</script>

<template>
  <section id="travelers" class="audience-section travelers tone-lake" aria-labelledby="travelers-title">
    <div class="audience-inner">
      <AudienceCopy :group="travelers">
        <NuxtLink class="text-link" to="/trip/demo">See a full sample trip <LwIcon name="arrow" /></NuxtLink>
      </AudienceCopy>

      <article class="day-card" aria-label="Sample day plan">
        <header>
          <div>
            <span class="day-tag">Sample plan</span>
            <h3>Saturday in Calamba</h3>
            <p>From a stay in Pansol</p>
          </div>
          <dl class="day-stats">
            <div><dt>Stops</dt><dd>5</dd></div>
            <div><dt>Driving</dt><dd>~1 h</dd></div>
          </dl>
        </header>
        <ol class="timeline">
          <li v-for="stop in sampleDay" :key="stop.time">
            <span v-if="stop.leg" class="leg">
              <LwIcon :name="stop.leg.mode === 'drive' ? 'car' : 'walk'" />{{ stop.leg.text }}
            </span>
            <div class="stop">
              <time>{{ stop.time }}</time>
              <span :class="['stop-icon', `tone-${stop.tone}`]"><LwIcon :name="stop.icon" /></span>
              <div>
                <strong>{{ stop.title }}</strong>
                <span>{{ stop.note }}</span>
              </div>
            </div>
          </li>
        </ol>
      </article>
    </div>

    <div class="places-block">
      <h3 class="sub-heading">Places we plan around</h3>
      <p class="sub-text">Starting with Calamba. More of Laguna is on the way.</p>
      <ul class="place-grid">
        <li v-for="place in placeTypes" :key="place.title" :class="['place-card', `tone-${place.tone}`]">
          <span class="place-icon"><LwIcon :name="place.icon" /></span>
          <h4>{{ place.title }}</h4>
          <p>{{ place.text }}</p>
          <ul class="place-tags">
            <li v-for="tag in place.tags" :key="tag">{{ tag }}</li>
          </ul>
        </li>
      </ul>
    </div>
  </section>
</template>
