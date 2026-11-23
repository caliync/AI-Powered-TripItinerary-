<script setup lang="ts">
// Leaflet map of one day. Client-only: Leaflet touches window on import.
import L from 'leaflet'
import type { DayPlan, LatLng } from '~/types/itinerary'

const props = defineProps<{ day: DayPlan; stay: LatLng; selected?: number | null }>()
const emit = defineEmits<{ select: [number] }>()
let markers = new Map<number, L.Marker>()
const el = ref<HTMLElement>()
let map: L.Map | null = null
let layer: L.LayerGroup | null = null

function css(name: string) {
  return `rgb(${getComputedStyle(document.documentElement).getPropertyValue(`--${name}`).trim().replace(/ /g, ',')})`
}

function draw() {
  if (!map) return
  layer?.remove()
  layer = L.layerGroup().addTo(map)
  markers = new Map()
  const mango = css('mango')
  const lake = css('lake')
  const bounds = L.latLngBounds([[props.stay.lat, props.stay.lng]])
  for (const leg of props.day.legs) {
    const pts = decodePolyline6(leg.geometry)
    L.polyline(pts, { color: mango, weight: 5, opacity: 0.95, lineCap: 'round' }).addTo(layer)
    pts.forEach(p => bounds.extend(p))
  }
  L.marker([props.stay.lat, props.stay.lng], {
    icon: L.divIcon({ className: '', html: `<div style="width:18px;height:18px;border-radius:5px;background:${lake};border:3px solid white"></div>`, iconSize: [18, 18] }),
    title: 'Where you stay',
  }).addTo(layer)
  for (const s of props.day.stops) {
    const m = L.marker([s.place.coords.lat, s.place.coords.lng], { icon: pin(s.order, false), title: s.place.name }).addTo(layer)
    m.on('click', () => emit('select', s.order))
    markers.set(s.order, m)
  }
  map.fitBounds(bounds, { padding: [28, 28] })
  paintSelected()
}

// The picked stop turns lake blue and larger, so a card and its pin are easy to match.
function pin(order: number, on: boolean) {
  const size = on ? 34 : 26
  const bg = on ? css('lake') : css('mango')
  const fg = on ? '#fff' : '#15262b'
  return L.divIcon({
    className: '', iconSize: [size, size],
    html: `<div style="width:${size}px;height:${size}px;border-radius:999px;background:${bg};color:${fg};font-weight:800;display:grid;place-items:center;border:3px solid white;font-size:${on ? 15 : 13}px;box-shadow:0 2px 8px rgba(0,0,0,.3)">${order + 1}</div>`,
  })
}
function paintSelected() {
  markers.forEach((m, order) => {
    const on = order === props.selected
    m.setIcon(pin(order, on))
    m.setZIndexOffset(on ? 1000 : 0)
  })
  const m = props.selected == null ? undefined : markers.get(props.selected)
  if (m && map) map.panTo(m.getLatLng())
}

onMounted(() => {
  map = L.map(el.value!, { zoomControl: true, attributionControl: true, scrollWheelZoom: false })
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19, attribution: '© OpenStreetMap contributors',
  }).addTo(map)
  draw()
})
watch(() => props.day, draw)
watch(() => props.selected, paintSelected)
watch(() => useTheme().theme.value, () => nextTick(draw))
onBeforeUnmount(() => map?.remove())
</script>

<template>
  <div ref="el" class="h-full w-full rounded-[20px] overflow-hidden border border-line" role="img" :aria-label="`Map of ${day.stops.length} stops for this day`" />
</template>
