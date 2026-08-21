import type { PersonalizedConstraints } from './api/client'

export type PersonalizedDefaults = PersonalizedConstraints & { category: 'conservative' | 'moderate' | 'aggressive'; confidence: number }
const KEY = 'optivest.personalized-defaults'

export function savePersonalizedDefaults(defaults: PersonalizedDefaults): void { localStorage.setItem(KEY, JSON.stringify(defaults)) }
export function loadPersonalizedDefaults(): PersonalizedDefaults | null { const stored=localStorage.getItem(KEY);return stored?JSON.parse(stored) as PersonalizedDefaults:null }
