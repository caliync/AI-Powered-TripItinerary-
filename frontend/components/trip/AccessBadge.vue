<script setup lang="ts">
// Wheelchair status for one place. Unknown is shown, never hidden (beta rule).
import type { AccessStatus } from '~/types/itinerary'
const props = defineProps<{ status: AccessStatus; rough?: boolean }>()
const text = computed(() => ({
  yes: 'Step-free',
  limited: 'Partly step-free',
  no: 'Not step-free',
  unknown: 'Access not checked',
}[props.status]))
const tone = computed(() => ({
  yes: 'text-moss bg-moss/10 border-moss/25',
  limited: 'text-caution bg-mango/15 border-mango/30',
  no: 'text-danger bg-danger/10 border-danger/25',
  unknown: 'text-muted bg-soft border-line',
}[props.status]))
</script>

<template>
  <span class="inline-flex items-center gap-1.5 rounded-pill border px-2.5 py-1 text-xs font-semibold" :class="tone">
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" aria-hidden="true">
      <circle cx="12" cy="4" r="2" /><path d="M12 7v6h5l2 6M12 13a5 5 0 1 0 4 7" />
    </svg>
    {{ text }}<template v-if="rough">, rough ground</template>
  </span>
</template>
