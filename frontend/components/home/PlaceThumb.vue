<script setup lang="ts">
// Drawn cover for a place card, one scene per kind of place. `seed` shifts the
// sun and hills so neighbouring cards don't look identical.
import type { FeaturedGroup, Motif } from '~/data/featuredPlaces'

const props = defineProps<{ group: FeaturedGroup; seed: number; motif?: Motif }>()
const DEFAULT: Record<FeaturedGroup, Motif> = { landmarks: 'church', hot_springs: 'pool', food: 'bowl', nature: 'trees' }
const m = computed(() => props.motif ?? DEFAULT[props.group])
const shift = computed(() => (props.seed * 37) % 60)
const palette = computed(() => ({
  landmarks: { sky: ['#f6c79a', '#fbe8d3'], ground: '#c9774f', deep: '#8d4a32' },
  hot_springs: { sky: ['#9ed3d6', '#e3f3f1'], ground: '#3d8f93', deep: '#24666c' },
  food: { sky: ['#f7cf7c', '#fdf0cf'], ground: '#e08f2c', deep: '#a9601a' },
  nature: { sky: ['#a9cfe8', '#e6f1f8'], ground: '#4f9a69', deep: '#2f6d4a' },
}[props.group]))
const gid = computed(() => `g-${props.group}-${props.seed}`)
</script>

<template>
  <svg viewBox="0 0 320 240" preserveAspectRatio="xMidYMid slice" class="h-full w-full" aria-hidden="true">
    <defs>
      <linearGradient :id="gid" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" :stop-color="palette.sky[0]" />
        <stop offset="1" :stop-color="palette.sky[1]" />
      </linearGradient>
    </defs>
    <rect width="320" height="240" :fill="`url(#${gid})`" />
    <circle :cx="200 + shift" :cy="96 + shift / 4" r="22" fill="#fff" opacity="0.6" />

    <template v-if="m === 'church'">
      <path :d="`M0 190 C 80 ${170 - shift / 4} 200 ${200 - shift / 5} 320 180 V240 H0Z`" :fill="palette.ground" opacity="0.5" />
      <!-- church front with a bell tower -->
      <g :fill="palette.deep">
        <rect x="118" y="112" width="84" height="88" />
        <path d="M112 116 L160 84 L208 116 Z" />
        <rect x="190" y="74" width="26" height="126" />
        <path d="M186 78 L203 58 L220 78 Z" />
      </g>
      <g fill="#fbe8d3">
        <path d="M148 200 V164 a12 12 0 0 1 24 0 V200 Z" />
        <circle cx="160" cy="132" r="7" />
        <rect x="199" y="96" width="8" height="14" rx="4" />
      </g>
      <rect y="198" width="320" height="42" :fill="palette.ground" />
    </template>

    <template v-else-if="m === 'pool'">
      <path :d="`M0 150 C 90 ${110 + shift / 3} 180 ${120 - shift / 4} 320 140 V240 H0Z`" :fill="palette.deep" opacity="0.45" />
      <rect x="40" y="160" width="240" height="56" rx="28" :fill="palette.ground" />
      <rect x="56" y="170" width="208" height="36" rx="18" fill="#bfe6e4" opacity="0.85" />
      <g fill="none" stroke="#fff" stroke-width="5" stroke-linecap="round" opacity="0.9">
        <path d="M120 150 c -10 -14 10 -22 0 -36 s 10 -22 0 -36" />
        <path d="M160 146 c -10 -14 10 -22 0 -36 s 10 -22 0 -36" />
        <path d="M200 150 c -10 -14 10 -22 0 -36 s 10 -22 0 -36" />
      </g>
    </template>

    <template v-else-if="m === 'bowl'">
      <rect y="176" width="320" height="64" :fill="palette.ground" opacity="0.55" />
      <ellipse cx="160" cy="190" rx="96" ry="14" :fill="palette.deep" opacity="0.35" />
      <path d="M76 140 H244 C 240 182 206 200 160 200 S 80 182 76 140Z" fill="#fff" />
      <path d="M76 140 H244" :stroke="palette.deep" stroke-width="6" stroke-linecap="round" />
      <ellipse cx="160" cy="140" rx="84" ry="10" fill="#f3e2c2" />
      <g fill="none" stroke="#fff" stroke-width="5" stroke-linecap="round" opacity="0.9">
        <path d="M130 120 c -8 -10 8 -16 0 -28" />
        <path d="M160 116 c -8 -10 8 -16 0 -28" />
        <path d="M190 120 c -8 -10 8 -16 0 -28" />
      </g>
    </template>

    <template v-else-if="m === 'tub'">
      <path :d="`M0 160 C 80 ${100 + shift / 2} 200 ${110 - shift / 4} 320 130 V240 H0Z`" :fill="palette.deep" opacity="0.5" />
      <rect y="196" width="320" height="44" fill="#d9c7aa" />
      <ellipse cx="160" cy="196" rx="92" ry="26" :fill="palette.ground" />
      <ellipse cx="160" cy="192" rx="76" ry="17" fill="#bfe6e4" />
      <g fill="none" stroke="#fff" stroke-width="5" stroke-linecap="round" opacity="0.9">
        <path d="M134 168 c -9 -12 9 -18 0 -30 s 9 -18 0 -30" />
        <path d="M186 168 c -9 -12 9 -18 0 -30 s 9 -18 0 -30" />
      </g>
      <g :fill="palette.deep">
        <path d="M262 196 C 262 150 258 120 250 96" :stroke="palette.deep" stroke-width="6" fill="none" />
        <path d="M250 96 c -24 -6 -40 6 -46 16 c 18 -8 32 -8 46 -16z M250 96 c 22 -10 40 -2 48 8 c -18 -4 -32 -4 -48 -8z M250 96 c -4 -20 4 -34 14 -40 c -4 16 -6 28 -14 40z" />
      </g>
    </template>

    <template v-else-if="m === 'house'">
      <rect y="196" width="320" height="44" :fill="palette.ground" />
      <!-- bahay na bato: stone base, wooden upper floor, hip roof -->
      <rect x="78" y="146" width="164" height="52" fill="#e8d2b6" />
      <rect x="70" y="104" width="180" height="44" :fill="palette.deep" />
      <path d="M58 106 L100 72 H220 L262 106 Z" fill="#7a3b26" />
      <g fill="#fbe8d3">
        <rect x="88" y="114" width="26" height="24" rx="2" /><rect x="128" y="114" width="26" height="24" rx="2" />
        <rect x="168" y="114" width="26" height="24" rx="2" /><rect x="208" y="114" width="26" height="24" rx="2" />
      </g>
      <path d="M146 198 V166 a14 14 0 0 1 28 0 V198 Z" :fill="palette.deep" />
    </template>

    <template v-else-if="m === 'pot'">
      <rect y="196" width="320" height="44" :fill="palette.ground" />
      <rect x="100" y="182" width="120" height="16" rx="4" fill="#e8d2b6" />
      <!-- the banga -->
      <path d="M132 86 h56 v10 c 0 6 -6 8 -6 14 c 26 10 44 34 44 54 c 0 12 -8 18 -18 18 h-90 c -10 0 -18 -6 -18 -18 c 0 -20 18 -44 44 -54 c 0 -6 -6 -8 -6 -14 z" fill="#a8542f" />
      <path d="M110 150 C 140 160 180 160 210 150" stroke="#fbe8d3" stroke-width="5" fill="none" opacity="0.7" />
    </template>

    <template v-else-if="m === 'monument'">
      <rect y="196" width="320" height="44" :fill="palette.ground" />
      <path d="M0 196 C 60 186 260 186 320 196" :fill="palette.ground" opacity="0.6" />
      <rect x="128" y="168" width="64" height="30" fill="#e8d2b6" />
      <rect x="140" y="128" width="40" height="42" fill="#d9bf9e" />
      <g :fill="palette.deep">
        <circle cx="160" cy="78" r="10" />
        <path d="M148 90 h24 l4 38 h-32 z" />
      </g>
      <g :fill="palette.deep" opacity="0.6">
        <circle cx="56" cy="160" r="22" /><rect x="53" y="170" width="6" height="28" />
        <circle cx="266" cy="156" r="26" /><rect x="263" y="168" width="6" height="30" />
      </g>
    </template>

    <template v-else-if="m === 'fish'">
      <rect y="176" width="320" height="64" :fill="palette.ground" opacity="0.55" />
      <!-- nipa cottage roof over a plate of fish -->
      <path d="M40 120 L160 60 L280 120 Z" fill="#b9874a" />
      <path d="M60 120 L160 72 L260 120" stroke="#8a5d2c" stroke-width="4" fill="none" />
      <rect x="70" y="120" width="8" height="70" fill="#8a5d2c" /><rect x="242" y="120" width="8" height="70" fill="#8a5d2c" />
      <ellipse cx="160" cy="186" rx="80" ry="16" fill="#fff" />
      <path d="M110 182 c 20 -18 60 -18 80 0 c -20 14 -60 14 -80 0 z M190 182 l18 -12 v24 z" fill="#5c8fb5" />
      <circle cx="126" cy="180" r="3" fill="#fff" />
    </template>

    <template v-else-if="m === 'lake'">
      <rect y="150" width="320" height="90" fill="#4f88b0" />
      <rect y="150" width="320" height="90" fill="#f7b46a" opacity="0.18" />
      <path d="M0 152 C 80 140 140 148 200 144 C 250 140 290 146 320 148 V152 H0 Z" fill="#6f93ad" />
      <g fill="#ffe1b3" opacity="0.8">
        <rect x="200" y="166" width="60" height="4" rx="2" /><rect x="190" y="184" width="84" height="3" rx="1.5" opacity="0.7" />
      </g>
      <!-- the baywalk railing -->
      <rect y="206" width="320" height="34" fill="#d8c6a8" />
      <g stroke="#8d6b47" stroke-width="4"><path d="M0 200 H320" /><path d="M20 200 v8 M70 200 v8 M120 200 v8 M170 200 v8 M220 200 v8 M270 200 v8" /></g>
    </template>

    <template v-else-if="m === 'wave'">
      <rect y="150" width="320" height="90" fill="#3f86b0" />
      <path d="M0 40 L320 30" stroke="#24566f" stroke-width="3" />
      <path d="M196 34 L176 140" stroke="#24566f" stroke-width="2" />
      <path d="M120 178 C 160 150 220 150 262 168" stroke="#fff" stroke-width="8" fill="none" stroke-linecap="round" opacity="0.9" />
      <g :fill="palette.deep">
        <circle cx="178" cy="118" r="8" /><path d="M172 128 h12 l6 26 h-24 z" />
      </g>
      <rect x="158" y="154" width="44" height="7" rx="3.5" fill="#f09e30" />
    </template>

    <template v-else>
      <path :d="`M0 170 C 70 ${120 + shift / 2} 150 ${130 - shift / 3} 220 150 C 260 160 290 150 320 140 V240 H0Z`" :fill="palette.ground" opacity="0.55" />
      <rect y="192" width="320" height="48" fill="#5d97bd" />
      <rect x="40" y="206" width="70" height="3" rx="1.5" fill="#fff" opacity="0.4" />
      <rect x="190" y="218" width="90" height="3" rx="1.5" fill="#fff" opacity="0.35" />
      <g :fill="palette.deep">
        <path d="M70 192 V150" :stroke="palette.deep" stroke-width="6" />
        <circle cx="70" cy="138" r="22" />
        <path d="M246 192 V158" :stroke="palette.deep" stroke-width="5" />
        <circle cx="246" cy="148" r="17" />
      </g>
    </template>
  </svg>
</template>
