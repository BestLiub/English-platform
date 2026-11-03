import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

const STORAGE_KEY = 'english:settings'

/** 生词注释策略 */
export type AnnotationStrategy = 'beyond' | 'unmastered' | 'all'

/** 把本地恢复的数值夹在允许范围内，避免手改 localStorage 后请求被后端拒绝 */
function clampNumber(value: unknown, min: number, max: number, fallback: number) {
  if (typeof value !== 'number' || !Number.isFinite(value)) return fallback
  return Math.min(max, Math.max(min, Math.round(value)))
}

export const useSettingsStore = defineStore('settings', () => {
  const dailyNewWords = ref(20)
  const dailyReviewLimit = ref(100)
  const activeWordbook = ref('cet4')
  const annotationStrategy = ref<AnnotationStrategy>('beyond')

  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const parsed = JSON.parse(raw)
      // 每日新词量：界面允许 5–100（后端上限 200）；每日复习上限：后端允许 0–1000
      dailyNewWords.value = clampNumber(parsed.dailyNewWords, 5, 100, dailyNewWords.value)
      dailyReviewLimit.value = clampNumber(
        parsed.dailyReviewLimit,
        0,
        1000,
        dailyReviewLimit.value
      )
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
