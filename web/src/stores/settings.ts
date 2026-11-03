import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

const STORAGE_KEY = 'english:settings'

/** 生词注释策略 */
export type AnnotationStrategy = 'beyond' | 'unmastered' | 'all'

export const useSettingsStore = defineStore('settings', () => {
  const dailyNewWords = ref(20)
  const dailyReviewLimit = ref(100)
  const activeWordbook = ref('cet4')
  const annotationStrategy = ref<AnnotationStrategy>('beyond')

  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const parsed = JSON.parse(raw)
      if (typeof parsed.dailyNewWords === 'number') dailyNewWords.value = parsed.dailyNewWords
      if (typeof parsed.dailyReviewLimit === 'number') dailyReviewLimit.value = parsed.dailyReviewLimit
      if (typeof parsed.activeWordbook === 'string') activeWordbook.value = parsed.activeWordbook
      if (['beyond', 'unmastered', 'all'].includes(parsed.annotationStrategy)) {
        annotationStrategy.value = parsed.annotationStrategy
      }
    }
  } catch {
    /* 配置坏了就用默认值 */
  }

  watch(
    [dailyNewWords, dailyReviewLimit, activeWordbook, annotationStrategy],
    () => {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          dailyNewWords: dailyNewWords.value,
          dailyReviewLimit: dailyReviewLimit.value,
          activeWordbook: activeWordbook.value,
          annotationStrategy: annotationStrategy.value
        })
      )
    },
    { deep: true }
  )

  return { dailyNewWords, dailyReviewLimit, activeWordbook, annotationStrategy }
})
