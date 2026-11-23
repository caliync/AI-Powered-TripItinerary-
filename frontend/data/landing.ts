// Copy and sample content for the home page sections (About us, Locals, Travelers, Contact).
// Text is Alli's approved homepage copy from Nov 20, 2026. Keep claims to what the planner does today.
import type { IconName } from './landingIcons'

export type Tone = 'lake' | 'mango' | 'clay' | 'forest'

// The menu, in Alli's order. Each id is a section on the home page.
export const navLinks = [
  { id: 'about', label: 'About us' },
  { id: 'locals', label: 'Locals' },
  { id: 'travelers', label: 'Travelers' },
  { id: 'contact', label: 'Contact' },
]

export const values: { icon: IconName; title: string; text: string; tone: Tone }[] = [
  {
    icon: 'mountain',
    title: 'Made for Laguna',
    text: 'We’re starting with Calamba and adding more Laguna towns one at a time, so every plan sticks to places we know.',
    tone: 'forest',
  },
  {
    icon: 'car',
    title: 'Less time on the road',
    text: 'Each day starts and ends at your stay and keeps to one area, so you spend the day at places, not in traffic.',
    tone: 'lake',
  },
  {
    icon: 'access',
    title: 'Honest about access',
    text: 'We show wheelchair access where we know it, and flag the places where we don’t, so you can decide for yourself.',
    tone: 'clay',
  },
  {
    icon: 'guide',
    title: 'Built with locals',
    text: 'Café owners, guides and residents can add or update their places, and share the routes they love.',
    tone: 'mango',
  },
]

export const steps: { icon: IconName; title: string; description: string }[] = [
  {
    icon: 'pin',
    title: 'Tell us where you stay',
    description: 'Your hotel or resort is the start and end of every day, so drives stay short.',
  },
  {
    icon: 'calendar',
    title: 'Pick your days and interests',
    description: 'Choose dates, who is going, your budget and anything we should plan around.',
  },
  {
    icon: 'route',
    title: 'Get a day-by-day route',
    description: 'Each day covers one area in a sensible loop, with meals at the right time. Swap any stop.',
  },
]

export type Audience = {
  id: 'locals' | 'travelers'
  title: string
  text: string
  icon: IconName
  points: { icon: IconName; label: string }[]
  cta: { to: string; label: string }
}

export const locals: Audience = {
  id: 'locals',
  title: 'Locals',
  text: 'Share what you love about your city by creating routes packed with local tips and hidden gems most visitors wouldn’t find on their own. You’ll earn tips and ratings from travelers who use your route—and if it’s really great, it can keep earning for you over time while helping others have an amazing trip.',
  icon: 'guide',
  points: [
    { icon: 'gem', label: 'Share hidden gems' },
    { icon: 'star', label: 'Get rated by travelers' },
    { icon: 'tip', label: 'Earn tips over time' },
  ],
  // Route sharing is a planned feature, so the button goes to Contact for now.
  cta: { to: '/#contact', label: 'Create a route' },
}

export const travelers: Audience = {
  id: 'travelers',
  title: 'Travelers',
  text: 'Tell us where you’re staying, your dates and what you enjoy. We plan each day as one easy loop from your stay, with drive times between stops, meals at the right time and accessibility notes where we have them. Don’t like a stop? Swap it for a nearby one.',
  icon: 'compass',
  points: [
    { icon: 'hotel', label: 'Planned around your stay' },
    { icon: 'food', label: 'Meals at mealtime' },
    { icon: 'route', label: 'Swap any stop' },
  ],
  cta: { to: '/plan', label: 'Plan my trip' },
}

export const earnSteps: { icon: IconName; title: string; text: string }[] = [
  { icon: 'route', title: 'Create a route', text: 'Pin the spots you love and add your own tips for each stop.' },
  { icon: 'star', title: 'Travelers use it', text: 'Visitors follow your route and rate it after their trip.' },
  { icon: 'tip', title: 'Earn tips over time', text: 'A great route keeps earning tips for as long as people use it.' },
]

export const placeTypes: { icon: IconName; title: string; text: string; tone: Tone; tags: string[] }[] = [
  { icon: 'spring', title: 'Hot springs', text: 'Spring pools planned as a slow afternoon near your stay.', tone: 'lake', tags: ['Pansol', 'Afternoons'] },
  { icon: 'heritage', title: 'Heritage', text: 'The Rizal Shrine and the old town church a short walk away.', tone: 'clay', tags: ['Rizal Shrine', 'Old town'] },
  { icon: 'food', title: 'Local food', text: 'Carinderias, bakeries and buko pie stops, timed for real mealtimes.', tone: 'mango', tags: ['Lunch', 'Pasalubong'] },
  { icon: 'mountain', title: 'Mt. Makiling', text: 'Nature stops and viewpoints on the slopes of the mountain.', tone: 'forest', tags: ['Nature', 'Views'] },
  { icon: 'leaf', title: 'Farms and parks', text: 'Open-air stops that suit families and slower days.', tone: 'forest', tags: ['Families', 'Outdoors'] },
  { icon: 'access', title: 'Access notes', text: 'Step-free and low-walking details shown where we have them.', tone: 'lake', tags: ['Wheelchair', 'Low walking'] },
]

export type SampleStop = {
  time: string
  title: string
  note: string
  icon: IconName
  tone: Tone
  leg?: { mode: 'drive' | 'walk'; text: string }
}

export const sampleDay: SampleStop[] = [
  { time: '9:00 AM', title: 'Leave your hotel in Pansol', note: 'Start of the loop', icon: 'hotel', tone: 'lake' },
  { time: '9:30 AM', title: 'Rizal Shrine', note: 'About 1 hour', icon: 'heritage', tone: 'clay', leg: { mode: 'drive', text: '25 min drive' } },
  { time: '10:45 AM', title: 'Calamba old town and plaza', note: '45 min', icon: 'heritage', tone: 'clay', leg: { mode: 'walk', text: '5 min walk' } },
  { time: '12:00 PM', title: 'Lunch at a local carinderia', note: 'Mealtime stop', icon: 'food', tone: 'mango', leg: { mode: 'drive', text: '8 min drive' } },
  { time: '1:30 PM', title: 'Hot spring afternoon', note: 'Back near your stay', icon: 'spring', tone: 'lake', leg: { mode: 'drive', text: '25 min drive' } },
]
