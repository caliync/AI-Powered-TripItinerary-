<script setup lang="ts">
// Contact: for businesses and anyone with questions. The button opens the add-or-update form.
</script>

<template>
  <section id="contact" class="contact" aria-labelledby="contact-title">
    <div class="section-heading">
      <h2 id="contact-title">Contact</h2>
      <p>Run a café, farm or attraction in Calamba? Questions or ideas? Reach out.</p>
    </div>
    <div class="contact-band">
      <svg class="contact-route" viewBox="0 0 420 220" aria-hidden="true">
        <path d="M10 190C80 200 120 150 170 120S260 110 300 70 360 20 410 30" />
        <circle cx="10" cy="190" r="6" />
        <circle cx="170" cy="120" r="6" />
        <circle cx="300" cy="70" r="6" />
      </svg>
      <span class="contact-icon"><LwIcon name="store" /></span>
      <div class="contact-copy">
        <h3>Add or update your place</h3>
        <p>Add your café, farm or attraction, or correct its hours, so travelers find it on the right day.</p>
      </div>
      <NuxtLink class="contact-button" to="/business">Add or update a place <LwIcon name="arrow" /></NuxtLink>
    </div>
  </section>
</template>
