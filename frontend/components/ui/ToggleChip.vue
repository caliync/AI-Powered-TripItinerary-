<script setup lang="ts">
// Checkbox styled as a chip; binds to an array of values.
defineProps<{ value: string; label: string }>()
const model = defineModel<string[]>({ required: true })
</script>

<template>
  <label
    class="relative inline-flex items-center gap-2 rounded-pill border px-4 min-h-[44px] cursor-pointer select-none bg-surface transition-shadow"
    :class="model.includes(value) ? 'border-lake ring-1 ring-lake bg-lake-soft/60' : 'border-line hover:border-ink/40 hover:shadow-sm'"
  >
    <input v-model="model" type="checkbox" :value="value" class="sr-only peer">
    <svg v-if="model.includes(value)" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" class="text-lake" aria-hidden="true"><path d="M5 12l5 5L20 7" /></svg>
    <span class="font-medium text-[15px]">{{ label }}</span>
    <span class="pointer-events-none absolute inset-0 rounded-pill peer-focus-visible:outline peer-focus-visible:outline-3 peer-focus-visible:outline-mango" aria-hidden="true" />
  </label>
</template>
