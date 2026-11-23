// Display helpers. Times arrive as Asia/Manila local "HH:MM:SS".

export function clock(hms: string): string {
  const [h, m] = hms.split(':').map(Number)
  const suffix = h >= 12 ? 'PM' : 'AM'
  const h12 = h % 12 === 0 ? 12 : h % 12
  return `${h12}:${String(m).padStart(2, '0')} ${suffix}`
}

export function minutes(seconds: number): string {
  const m = Math.max(1, Math.round(seconds / 60))
  if (m < 60) return `${m} min`
  const h = Math.floor(m / 60)
  const r = m % 60
  return r ? `${h} h ${r} min` : `${h} h`
}

export function km(meters: number): string {
  return meters < 1000 ? `${Math.round(meters)} m` : `${(meters / 1000).toFixed(1)} km`
}

export function dayLabel(iso: string): string {
  const d = new Date(`${iso}T00:00:00+08:00`)
  return d.toLocaleDateString('en-PH', { weekday: 'short', month: 'short', day: 'numeric', timeZone: 'Asia/Manila' })
}

export function signedMinutes(seconds: number): string {
  if (Math.abs(seconds) < 30) return 'Same drive time'
  const m = Math.round(Math.abs(seconds) / 60)
  return seconds < 0 ? `${m} min shorter drive` : `${m} min longer drive`
}

/** Today's date in Calamba as YYYY-MM-DD, for date pickers that block past days. */
export function todayInManila(): string {
  return new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Manila' })
}

export function pesos(n: number): string {
  return `₱${n.toLocaleString('en-PH')}`
}
