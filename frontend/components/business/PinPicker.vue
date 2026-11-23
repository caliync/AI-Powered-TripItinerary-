<script setup lang="ts">
// Tap the map to drop the business pin. Starts on Calamba old town.
// Plain component (not .client): the app runs with ssr off, and the .client
// wrapper dropped the template ref alongside defineModel.
import L from 'leaflet'
import type { LatLng } from '~/types/itinerary'

const model = defineModel<LatLng | null>({ required: true })
const el = ref<HTMLElement>()
let map: L.Map | null = null
let pin: L.Marker | null = null

function place(p: LatLng) {
  const icon = L.divIcon({ className: '', html: '<div style="width:22px;height:22px;border-radius:999px 999px 999px 0;transform:rotate(-45deg);background:rgb(222,145,30);border:3px solid white"></div>', iconSize: [22, 22], iconAnchor: [11, 22] })
  pin ? pin.setLatLng(p) : (pin = L.marker(p, { icon }).addTo(map!))
}

onMounted(() => {
  map = L.map(el.value!, { scrollWheelZoom: false }).setView([14.2117, 121.1653], 14)
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '© OpenStreetMap contributors' }).addTo(map)
  map.on('click', (e: L.LeafletMouseEvent) => { model.value = { lat: +e.latlng.lat.toFixed(6), lng: +e.latlng.lng.toFixed(6) } })
  if (model.value) place(model.value)
})
watch(model, v => v && place(v))
onBeforeUnmount(() => map?.remove())
</script>

<template>
  <div ref="el" class="h-64 w-full rounded-[14px] overflow-hidden border border-line" role="application" aria-label="Map. Click where your business is." />
</template>
