import { defineStore } from 'pinia'
import { ref } from 'vue'
import { get } from '@/api/client'

export interface DailyPoint {
  date: string
  total: number
  good: number
}

export interface StatsData {
  daily: DailyPoint[]
  total_reviews: number
  good_reviews: number
  learned_words: number
}

export const useStatsStore = defineStore('stats', () => {
  const data = ref<StatsData | null>(null)
  const days = ref(30)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function load(range?: number) {
    if (typeof range === 'number') days.value = range
    loading.value = true
    error.value = null
    try {
      data.value = await get<StatsData>('/study/stats', { days: days.value })
    } catch (e) {
      error.value = (e as Error).message
    } finally {
      loading.value = false
    }
  }

  return { data, days, loading, error, load }
})
