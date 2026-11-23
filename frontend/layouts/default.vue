<script setup lang="ts">
// Site header and footer from Alli's homepage draft (Nov 20). Their styles live in
// assets/css/landing.css under .lw-home; the wrapper uses display: contents so the
// header can stay sticky.
import { navLinks } from '~/data/landing'

const { theme, toggle } = useTheme()
const route = useRoute()
const menuOpen = ref(false)
watch(() => route.fullPath, () => (menuOpen.value = false))

function onKey(event: KeyboardEvent) {
  if (event.key === 'Escape') menuOpen.value = false
}
onMounted(() => window.addEventListener('keydown', onKey))
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))

// On the home page, the menu link for the section on screen is highlighted.
const active = useActiveSection(navLinks.map((link) => link.id))
const current = (id: string) => (route.path === '/' && active.value === id ? 'location' : undefined)
</script>

<template>
  <div class="min-h-dvh flex flex-col font-sans">
    <a href="#main" class="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 z-[1300] bg-surface px-3 py-2 rounded-card">Skip to content</a>

    <div class="lw-home lw-chrome">
      <header class="site-header">
        <NuxtLink class="brand" to="/" aria-label="LakbayWise home">
          <span class="brand-mark"><img src="/img/lakbaywise-pin.png" alt=""></span>
          <span class="brand-word">LAKBAYWISE</span>
        </NuxtLink>

        <nav class="desktop-nav" aria-label="Main navigation">
          <NuxtLink v-for="link in navLinks" :key="link.id" :to="`/#${link.id}`" :aria-current="current(link.id)">
            {{ link.label }}
          </NuxtLink>
        </nav>

        <div class="header-actions">
          <button class="icon-button" type="button" :aria-label="theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'"
            :aria-pressed="theme === 'dark'" @click="toggle">
            <LwIcon :name="theme === 'dark' ? 'sun' : 'moon'" />
          </button>
          <button class="icon-button menu-button" type="button" :aria-expanded="menuOpen" aria-controls="mobile-menu"
            :aria-label="menuOpen ? 'Close menu' : 'Open menu'" @click="menuOpen = !menuOpen">
            <LwIcon :name="menuOpen ? 'close' : 'menu'" />
          </button>
        </div>

        <nav v-if="menuOpen" id="mobile-menu" class="mobile-nav" aria-label="Main navigation">
          <NuxtLink v-for="link in navLinks" :key="link.id" :to="`/#${link.id}`" :aria-current="current(link.id)">
            {{ link.label }}
          </NuxtLink>
        </nav>
      </header>
    </div>

    <main id="main" class="flex-1">
      <slot />
    </main>

    <div class="lw-home lw-chrome">
      <footer class="site-footer">
        <div class="footer-inner">
          <NuxtLink class="brand brand-small" to="/" aria-label="LakbayWise home">
            <span class="brand-mark"><img src="/img/lakbaywise-pin.png" alt=""></span>
            <span class="brand-word">LAKBAYWISE</span>
          </NuxtLink>
          <nav aria-label="Footer">
            <NuxtLink v-for="link in navLinks" :key="link.id" :to="`/#${link.id}`">{{ link.label }}</NuxtLink>
          </nav>
          <p>
            © 2026 LakbayWise. Beta, Calamba only. Map data ©
            <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>.
          </p>
        </div>
      </footer>
    </div>
  </div>
</template>
