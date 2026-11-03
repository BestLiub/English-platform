import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { get, post } from '@/api/client'

export interface PlanItem {
  word_id: number
  word: string
  phonetic: string | null
  translation: string | null
  is_new: boolean
}

export interface StudyPlan {
  reviews: PlanItem[]
  new_words: PlanItem[]
}

/** 一张卡片的三种结局 */
export type Outcome = 'skipped' | 'unknown' | 'vague'

export const OUTCOME_LABELS: Record<Outcome, string> = {
  skipped: '跳过',
  unknown: '不认识',
  vague: '记忆模糊'
}

export const useStudyStore = defineStore('study', () => {
  const plan = ref<StudyPlan>({ reviews: [], new_words: [] })
  const loading = ref(false)
  const error = ref<string | null>(null)

  // 一次学习会话的状态：队列里复习卡在前、新词在后
  const queue = ref<PlanItem[]>([])
  const index = ref(0)
  const revealed = ref(false)
  const submitting = ref(false)
  const shownAt = ref(0)
  const tally = ref<Record<Outcome, number>>({ skipped: 0, unknown: 0, vague: 0 })

  const current = computed<PlanItem | null>(() => queue.value[index.value] ?? null)
  const total = computed(() => queue.value.length)
  const started = computed(() => queue.value.length > 0)
  const finished = computed(() => queue.value.length > 0 && index.value >= queue.value.length)
  const progress = computed(() =>
    total.value ? Math.round((index.value / total.value) * 100) : 0
  )

  async function loadPlan(params?: { wordbook?: string; new_limit?: number; reviewLimit?: number }) {
    loading.value = true
    error.value = null
    try {
      plan.value = await get<StudyPlan>('/study/plan', {
        wordbook: params?.wordbook,
        new_limit: params?.new_limit,
        review_limit: params?.reviewLimit
      })
    } catch (e) {
      error.value = (e as Error).message
    } finally {
      loading.value = false
    }
  }

  /** 拉一份新计划并开始学习；重复进入时不会叠加旧队列 */
  async function startSession(opts: { wordbook: string; newLimit: number; reviewLimit: number }) {
    loading.value = true
    error.value = null
    try {
      plan.value = await get<StudyPlan>('/study/plan', {
        wordbook: opts.wordbook,
        new_limit: opts.newLimit,
        review_limit: opts.reviewLimit
      })
      queue.value = [...plan.value.reviews, ...plan.value.new_words]
      index.value = 0
      revealed.value = false
      tally.value = { skipped: 0, unknown: 0, vague: 0 }
      shownAt.value = Date.now()
    } catch (e) {
      error.value = (e as Error).message
      queue.value = []
    } finally {
      loading.value = false
    }
  }

  function reveal() {
    if (current.value && !revealed.value) revealed.value = true
  }

  function advance() {
    index.value += 1
    revealed.value = false
    shownAt.value = Date.now()
  }

  /** 一眼就会：永久标记为已掌握，以后不再出现 */
  async function skip() {
    const item = current.value
    if (!item || revealed.value || submitting.value) return

    submitting.value = true
    try {
      await post('/study/skip', { word_id: item.word_id })
      tally.value.skipped += 1
      advance()
    } catch {
      // 拦截器已提示，停在当前卡片让用户重试
    } finally {
      submitting.value = false
    }
  }

  /**
   * 看过释义 = 这个词需要复习，统一按「没记住」提交。
   * 不认识 / 记忆模糊 只是用户自己的判断，不区分地传给后端。
   */
  async function grade(outcome: 'unknown' | 'vague') {
    const item = current.value
    if (!item || !revealed.value || submitting.value) return

    submitting.value = true
    try {
      await post('/study/review', {
        word_id: item.word_id,
        rating: 1,
        // 超过 10 分钟的记为 10 分钟，避免中途离开把统计带偏
        elapsed_ms: Math.min(Date.now() - shownAt.value, 600_000)
      })
      tally.value[outcome] += 1
      advance()
    } catch {
      // 同上
    } finally {
      submitting.value = false
    }
  }

  function reset() {
    queue.value = []
    index.value = 0
    revealed.value = false
    tally.value = { skipped: 0, unknown: 0, vague: 0 }
  }

  return {
    plan,
    loading,
    error,
    queue,
    index,
    current,
    total,
    started,
    finished,
    progress,
    revealed,
    submitting,
    tally,
    loadPlan,
    startSession,
    reveal,
    skip,
    grade,
    reset
  }
})
