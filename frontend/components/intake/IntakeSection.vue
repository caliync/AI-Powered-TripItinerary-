<script setup lang="ts">
// The intake is a real sequence of five questions, so sections are numbered.
defineProps<{ step: number; title: string; hint?: string; error?: string; optional?: boolean }>()
</script>

<template>
  <fieldset class="grid grid-cols-[2.25rem_1fr] gap-x-4 py-7 border-t border-line first:border-t-0">
    <span class="h-9 w-9 rounded-pill grid place-items-center font-bold text-sm" :class="error ? 'bg-danger/10 text-danger' : 'bg-lake-soft text-lake'" aria-hidden="true">{{ step }}</span>
    <div class="min-w-0">
      <legend class="contents">
        <span class="block text-xl font-bold tracking-tight">{{ title }}<span v-if="optional" class="ml-2 text-sm font-medium text-muted">optional</span></span>
      </legend>
      <p v-if="hint" class="text-muted mt-1">{{ hint }}</p>
      <div class="mt-4">
        <slot />
      </div>
      <p v-if="error" class="mt-2 text-sm font-medium text-danger">{{ error }}</p>
    </div>
  </fieldset>
</template>
