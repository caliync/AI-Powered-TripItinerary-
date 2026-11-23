<script setup lang="ts">
// Locals: Alli's copy about sharing routes, with the three steps of how locals earn.
// Route sharing is planned, not built yet.
import { earnSteps, locals } from '~/data/landing'
</script>

<template>
  <section id="locals" class="audience-section tone-mango" aria-labelledby="locals-title">
    <div class="audience-inner">
      <AudienceCopy :group="locals" />
      <ol class="earn-steps" aria-label="How locals earn">
        <li v-for="(step, index) in earnSteps" :key="step.title">
          <span class="earn-icon"><LwIcon :name="step.icon" /></span>
          <div>
            <span class="earn-count">Step {{ index + 1 }}</span>
            <strong>{{ step.title }}</strong>
            <p>{{ step.text }}</p>
          </div>
        </li>
      </ol>
    </div>
  </section>
</template>
