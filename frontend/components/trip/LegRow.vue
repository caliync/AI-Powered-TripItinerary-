<script setup lang="ts">
// The drive between two stops, drawn as a segment of the route ribbon.
import type { Leg } from '~/types/itinerary'
defineProps<{ leg: Leg }>()
</script>

<template>
  <div class="relative pl-12 py-2.5 text-sm font-medium text-muted flex flex-wrap items-center gap-2">
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
      <path d="M5 17h14M6 17l1.5-6h9L18 17M8 11l1-3h6l1 3" /><circle cx="8" cy="17" r="1.5" /><circle cx="16" cy="17" r="1.5" />
    </svg>
    <span>{{ minutes(leg.duration_s) }} drive, {{ km(leg.distance_m) }}</span>
    <span v-if="leg.traffic_factor > 1.05" class="rounded-pill bg-mango/15 text-caution px-2 py-0.5 text-xs font-medium">
      Rush hour, planned at {{ leg.traffic_factor }}× normal
    </span>
  </div>
</template>
