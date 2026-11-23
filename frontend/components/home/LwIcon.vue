<script setup lang="ts">
// One of the two-tone homepage icons. Decorative: the text next to it carries the meaning.
import { icons, type IconName } from '~/data/landingIcons'

defineProps<{ name: IconName }>()
</script>

<template>
  <!-- eslint-disable-next-line vue/no-v-html -- static, repo-owned SVG paths -->
  <svg class="lw-icon" viewBox="0 0 24 24" aria-hidden="true" v-html="icons[name]" />
</template>
