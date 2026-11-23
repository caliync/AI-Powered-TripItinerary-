<script setup lang="ts">
// Landing page from Alli's homepage draft: the photo hero and planner, then the sections
// the menu links to (About us, Locals, Travelers, Contact).
useHead({ title: 'LakbayWise: plan a day in Laguna around where you stay' })
</script>

<template>
  <div class="lw-home">
    <HomeHero />
    <AboutSection />
    <LocalsSection />
    <TravelersSection />
    <ContactSection />
  </div>
</template>
