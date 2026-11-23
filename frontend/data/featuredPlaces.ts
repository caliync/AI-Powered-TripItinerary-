// Places shown on the home page. Taken from the approved and walk-in rows of
// the Sheet (Places and Calamba_All_Places tabs, Nov 18 2026). Descriptions are
// short paraphrases of the Places tab. No private resorts here.
import type { AccessStatus, Interest } from '~/types/itinerary'

export type FeaturedGroup = 'landmarks' | 'hot_springs' | 'food' | 'nature'

export interface FeaturedPlace {
  id: string
  name: string
  area: string
  group: FeaturedGroup
  interest: Interest | 'landmark'
  blurb: string
  access: AccessStatus
  popular?: boolean
  motif?: Motif
}

export type Motif = 'church' | 'house' | 'pot' | 'monument' | 'pool' | 'tub' | 'bowl' | 'fish' | 'lake' | 'trees' | 'wave'

export const FEATURED_GROUPS: Array<{ value: FeaturedGroup | 'popular'; label: string }> = [
  { value: 'popular', label: 'Popular' },
  { value: 'landmarks', label: 'Landmarks' },
  { value: 'hot_springs', label: 'Hot springs' },
  { value: 'food', label: 'Food' },
  { value: 'nature', label: 'Parks & lake' },
]

export const FEATURED_PLACES: FeaturedPlace[] = [
  { id: 'osm:way/93587272', name: 'Rizal Shrine', motif: 'house', area: 'Poblacion', group: 'landmarks', interest: 'landmark', access: 'unknown', popular: true,
    blurb: 'The restored house where José Rizal was born, now a museum.' },
  { id: 'osm:way/170221744', name: 'La Vista Pansol', area: 'Pansol', group: 'hot_springs', interest: 'hot_springs', access: 'limited', popular: true,
    blurb: 'Warm spring pools, slides and picnic huts for a family day.' },
  { id: 'osm:way/530235297', name: 'Calamba Baywalk', motif: 'lake', area: 'Lingga', group: 'nature', interest: 'parks', access: 'limited', popular: true,
    blurb: 'A free lakeside walk with food stalls and sunsets over Laguna de Bay.' },
  { id: 'osm:way/530206615', name: 'Samaral Seafood', motif: 'fish', area: 'Halang', group: 'food', interest: 'seafood', access: 'unknown', popular: true,
    blurb: 'Filipino seafood served in bamboo and nipa cottages.' },
  { id: 'osm:way/87216378', name: 'Calamba Church', area: 'Poblacion', group: 'landmarks', interest: 'landmark', access: 'unknown', popular: true,
    blurb: 'The 19th-century parish church where Rizal was baptised.' },
  { id: 'osm:relation/13509285', name: 'Sol Y Viento', motif: 'tub', area: 'Pansol', group: 'hot_springs', interest: 'hot_springs', access: 'unknown', popular: true,
    blurb: 'Mountain hot spring resort with pools, jacuzzis and a restaurant.' },
  { id: 'osm:way/746912736', name: 'Calamba Banga', motif: 'pot', area: 'Poblacion', group: 'landmarks', interest: 'landmark', access: 'yes', popular: true,
    blurb: 'The giant clay pot from 1937 that became the city symbol.' },
  { id: 'osm:way/109338570', name: "Tuding's Original Porkchop", area: 'Real', group: 'food', interest: 'traditional_food', access: 'unknown', popular: true,
    blurb: 'Porkchop and rice plates on Real Road.' },
  { id: 'osm:way/409890076', name: 'Rizal Monument', motif: 'monument', area: 'Real', group: 'landmarks', interest: 'landmark', access: 'unknown',
    blurb: 'The Rizal statue and plaza in front of the new City Hall.' },
  { id: 'osm:node/10207392274', name: 'Herbal Resort', motif: 'tub', area: 'Bucal', group: 'hot_springs', interest: 'hot_springs', access: 'unknown',
    blurb: 'Hot spring pools with day swims and night swims.' },
  { id: 'osm:relation/13509301', name: 'Monte Vista Calamba', area: 'Pansol', group: 'hot_springs', interest: 'hot_springs', access: 'unknown',
    blurb: 'Hot spring pools on the slope of Mt. Makiling.' },
  { id: 'osm:node/1238550504', name: 'Aling Inday Lugawan', area: 'Poblacion', group: 'food', interest: 'traditional_food', access: 'unknown',
    blurb: 'Rice porridge one block from the church.' },
  { id: 'osm:node/1737935263', name: 'Tita Sally Restaurant', area: 'Pansol', group: 'food', interest: 'traditional_food', access: 'unknown',
    blurb: 'Filipino lunch near the Pansol hot springs.' },
  { id: 'osm:way/487112992', name: 'Laguna Wildlife Park', motif: 'trees', area: 'Pansol', group: 'nature', interest: 'parks', access: 'unknown',
    blurb: 'A rescue centre and park at the foot of Mt. Makiling.' },
  { id: 'osm:way/281980715', name: 'Republ1c Wakepark', motif: 'wave', area: 'Canlubang', group: 'nature', interest: 'parks', access: 'unknown',
    blurb: 'Cable wakeboarding at Nuvali in Canlubang.' },
  { id: 'osm:way/779540829', name: 'San Pedro Calungsod Church', area: 'La Mesa', group: 'landmarks', interest: 'landmark', access: 'unknown',
    blurb: 'A parish church in Villa de Calamba, La Mesa.' },
]
