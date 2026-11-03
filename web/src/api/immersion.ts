import { get, post } from './client'

export interface ImmersionWord {
  word_id: number
  word: string
  phonetic: string | null
  translation: string | null
}

export interface ImmersionProgress {
  total: number
  mastered: number
  remaining: number
}

export interface NextResult {
  word: ImmersionWord | null
  progress: ImmersionProgress
  finished: boolean
}

export const fetchNext = (wordbook: string) =>
  post<NextResult>('/immersion/next', { wordbook })

export const skipWord = (wordbook: string, wordId: number) =>
  post<ImmersionProgress>('/immersion/skip', { word_id: wordId, wordbook })

export const resetImmersion = (wordbook: string) =>
  post<ImmersionProgress>('/immersion/reset', { wordbook })

export const fetchStats = (wordbook: string) =>
  get<ImmersionProgress>('/immersion/stats', { wordbook })
