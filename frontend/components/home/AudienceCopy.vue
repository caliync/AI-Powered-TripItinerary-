<script setup lang="ts">
// The text half of the Locals and Travelers sections: icon, heading, copy, chips and actions.
import type { Audience } from '~/data/landing'

defineProps<{ group: Audience }>()
</script>

<template>
  <div class="audience-copy">
    <span class="audience-icon"><LwIcon :name="group.icon" /></span>
    <h2 :id="`${group.id}-title`">{{ group.title }}</h2>
    <p>{{ group.text }}</p>
    <ul class="audience-points">
      <li v-for="point in group.points" :key="point.label">
        <LwIcon :name="point.icon" />{{ point.label }}
      </li>
    </ul>
    <div class="audience-actions">
      <NuxtLink class="audience-button" :to="group.cta.to">
        {{ group.cta.label }} <LwIcon name="arrow" />
      </NuxtLink>
      <slot />
    </div>
  </div>
</template>
