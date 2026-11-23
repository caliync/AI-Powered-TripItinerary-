<script setup lang="ts">
// One component for loading / error / empty, so every async view has all three.
defineProps<{ kind: 'loading' | 'error' | 'empty'; title: string; body?: string; actionLabel?: string }>()
defineEmits<{ action: [] }>()
</script>

<template>
  <div class="mx-auto max-w-md text-center py-16 px-4" :role="kind === 'error' ? 'alert' : 'status'" aria-live="polite">
    <div v-if="kind === 'loading'" class="mx-auto mb-4 h-1.5 w-40 overflow-hidden rounded-pill bg-lake-soft">
      <div class="h-full w-1/3 rounded-pill bg-mango animate-[slide_1.1s_ease-in-out_infinite]" />
    </div>
    <p class="font-semibold text-lg">{{ title }}</p>
    <p v-if="body" class="text-muted mt-1">{{ body }}</p>
    <button v-if="actionLabel" type="button" class="mt-5 rounded-pill bg-lake text-surface font-semibold px-6 min-h-[44px]" @click="$emit('action')">
      {{ actionLabel }}
    </button>
  </div>
</template>

<style>
@keyframes slide { 0% { transform: translateX(-100%); } 100% { transform: translateX(300%); } }
</style>
