<script setup lang="ts">
// Radio styled as a card. Use inside a <fieldset> with a <legend>.
defineProps<{ name: string; value: string; label: string; hint?: string }>()
const model = defineModel<string>({ required: true })
</script>

<template>
  <label
    class="relative flex flex-col gap-0.5 rounded-[14px] border px-4 py-3.5 cursor-pointer bg-surface transition-shadow"
    :class="model === value ? 'border-lake ring-1 ring-lake bg-lake-soft/60' : 'border-line hover:border-ink/40 hover:shadow-sm'"
  >
    <input v-model="model" type="radio" :name="name" :value="value" class="sr-only peer">
    <span class="font-semibold">{{ label }}</span>
    <span v-if="hint" class="text-sm text-muted">{{ hint }}</span>
    <span class="pointer-events-none absolute inset-0 peer-focus-visible:outline peer-focus-visible:outline-3 peer-focus-visible:outline-mango rounded-[14px]" aria-hidden="true" />
  </label>
</template>
