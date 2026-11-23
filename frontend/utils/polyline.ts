// Google encoded polyline, precision 6 (what OSRM returns with geometries=polyline6).
import type { LatLng } from '~/types/itinerary'

const FACTOR = 1e6

export function decodePolyline6(str: string): Array<[number, number]> {
  const out: Array<[number, number]> = []
  let i = 0
  let lat = 0
  let lng = 0
  while (i < str.length) {
    for (const axis of [0, 1]) {
      let shift = 0
      let result = 0
      let b: number
      do {
        b = str.charCodeAt(i++) - 63
        result |= (b & 0x1f) << shift
        shift += 5
      } while (b >= 0x20)
      const delta = result & 1 ? ~(result >> 1) : result >> 1
      if (axis === 0) lat += delta
      else lng += delta
    }
    out.push([lat / FACTOR, lng / FACTOR])
  }
  return out
}

/** Only used by mock data; the real API sends geometry already encoded. */
export function encodePolyline6(points: LatLng[]): string {
  let out = ''
  let prevLat = 0
  let prevLng = 0
  const enc = (v: number) => {
    let n = v < 0 ? ~(v << 1) : v << 1
    let s = ''
    while (n >= 0x20) {
      s += String.fromCharCode((0x20 | (n & 0x1f)) + 63)
      n >>= 5
    }
    return s + String.fromCharCode(n + 63)
  }
  for (const p of points) {
    const lat = Math.round(p.lat * FACTOR)
    const lng = Math.round(p.lng * FACTOR)
    out += enc(lat - prevLat) + enc(lng - prevLng)
    prevLat = lat
    prevLng = lng
  }
  return out
}
