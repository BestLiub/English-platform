import { defineStore } from 'pinia'
import { ref } from 'vue'
import { fetchNext, resetImmersion, skipWord, type ImmersionProgress, type ImmersionWord } from '@/api/immersion'

export const useImmersionStore = defineStore('immersion', () => {
  const word = ref<ImmersionWord | null>(null)
  const progress = ref<ImmersionProgress>({ total: 0, mastered: 0, remaining: 0 })
  const loading = ref(false)
  const submitting = ref(false)
  const finished = ref(false)

  async function next(wordbook: string) {
    loading.value = true
    try {
      const result = await fetchNext(wordbook)
      word.value = result.word
      progress.value = result.progress
      finished.value = result.finished
    } finally {
      loading.value = false
    }
  }

  async function skip(wordbook: string) {
    if (!word.value || submitting.value) return
    submitting.value = true
    try {
      progress.value = await skipWord(wordbook, word.value.word_id)
      await next(wordbook)
    } finally {
      submitting.value = false
    }
  }

  async function restart(wordbook: string) {
    if (submitting.value) return
    submitting.value = true
    try {
      progress.value = await resetImmersion(wordbook)
      finished.value = false
      await next(wordbook)
    } finally {
      submitting.value = false
    }
  }

  return { word, progress, loading, submitting, finished, next, skip, restart }
})
