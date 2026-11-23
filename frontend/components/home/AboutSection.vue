<script setup lang="ts">
// About us: who we are and what we care about, then the three steps of how it works.
import { steps, values } from '~/data/landing'
</script>

<template>
  <section id="about" class="how-it-works about" aria-labelledby="about-title">
    <div class="about-grid">
      <div class="about-intro">
        <h2 id="about-title">About us</h2>
        <p class="about-lead">
          We build efficient, accessible day trips across Laguna. Share your stay, schedule and interests,
          and receive a clear day-by-day route with drive times, meal stops and accessibility information
          where available.
        </p>
        <p>
          Planning a few days in Laguna usually means jumping between maps, old blog posts and group chats,
          then finding out two stops are an hour apart. LakbayWise puts it in one place: tell us where you’re
          staying and what you enjoy, and we turn it into days that make sense on the map.
        </p>
        <p>
          We’re starting in Calamba, home of the Rizal Shrine, the hot springs of Pansol and the foot of
          Mount Makiling. Once Calamba plans well, we’ll bring the same care to the rest of the province.
        </p>
      </div>

      <div class="about-values">
        <h3 class="values-title">What we care about</h3>
        <ul class="values">
          <li v-for="value in values" :key="value.title" :class="['value-card', `tone-${value.tone}`]">
            <div class="value-head">
              <span class="value-icon"><LwIcon :name="value.icon" /></span>
              <h4>{{ value.title }}</h4>
            </div>
            <p>{{ value.text }}</p>
          </li>
        </ul>
      </div>
    </div>

    <h3 class="sub-heading">How it works</h3>
    <ol class="steps">
      <li v-for="(step, index) in steps" :key="step.title" class="step">
        <div class="step-visual">
          <LwIcon :name="step.icon" />
          <span class="step-number" aria-hidden="true">{{ index + 1 }}</span>
        </div>
        <svg v-if="index < steps.length - 1" class="step-connector" viewBox="0 0 300 60" aria-hidden="true">
          <path d="M4 48C70 60 110 52 150 30S230 0 296 10" />
        </svg>
        <h4>{{ step.title }}</h4>
        <p>{{ step.description }}</p>
      </li>
    </ol>
  </section>
</template>
