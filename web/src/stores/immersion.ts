import { defineStore } from 'pinia'
import { ref } from 'vue'
import { fetchNext, resetImmersion, skipWord, type ImmersionProgress, type ImmersionWord } from '@/api/immersion'

export const useImmersionStore = defineStore('immersion', () => {
  const word = ref<ImmersionWord | null>(null)
  const progress = ref<ImmersionProgress>({ total: 0, mastered: 0, remaining: 0 })
  const loading = ref(false)
  const submitting = ref(false)
  const finished = ref(false)
  // 当前卡片是从哪个词库抽出来的：跳过和重置都以它为准，
  // 避免用户中途切换词库后把旧卡片的 word_id 提交到新词库
  const currentBook = ref('')

  async function next(wordbook: string) {
    loading.value = true
    try {
      const result = await fetchNext(wordbook)
      word.value = result.word
      progress.value = result.progress
      finished.value = result.finished
      currentBook.value = wordbook
    } finally {
      loading.value = false
    }
  }

  async function skip() {
    if (!word.value || !currentBook.value || submitting.value) return
    submitting.value = true
    try {
      progress.value = await skipWord(currentBook.value, word.value.word_id)
      await next(currentBook.value)
    } finally {
      submitting.value = false
    }
  }

  async function restart() {
    if (!currentBook.value || submitting.value) return
    submitting.value = true
    try {
      progress.value = await resetImmersion(currentBook.value)
      finished.value = false
      await next(currentBook.value)
    } finally {
      submitting.value = false
    }
  }

  /** 切换词库或离开页面时清空本地状态，防止旧词库的卡片/进度串到新词库 */
  function resetLocalState() {
    word.value = null
    progress.value = { total: 0, mastered: 0, remaining: 0 }
    finished.value = false
    currentBook.value = ''
  }

  return {
    word,
    progress,
    loading,
    submitting,
    finished,
    currentBook,
    next,
    skip,
    restart,
    resetLocalState
  }
})
