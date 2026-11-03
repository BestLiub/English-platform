import { del, get, patch, post, postForm, put } from './client'

export interface DocumentSummary {
  id: number
  title: string
  source_type: string
  source_ref: string | null
  word_count: number
  paragraph_count: number
  created_at: string
}

export interface Paragraph {
  idx: number
  text: string
}

export interface DocumentDetail extends DocumentSummary {
  paragraphs: Paragraph[]
  last_paragraph_idx: number
}

export interface AnnotationSpan {
  start: number
  end: number
  word: string
  translation: string | null
  word_id: number | null
}

export interface AnnotationMap {
  strategy: string
  paragraphs: Record<string, AnnotationSpan[]>
}

export interface DictEntry {
  word_id: number | null
  word: string
  phonetic: string | null
  translation: string | null
  definition: string | null
  frq: number | null
  tag: string | null
  lemma: string | null
  in_user_words: boolean
}

export const listDocuments = () => get<DocumentSummary[]>('/documents')

export const getDocument = (id: number) => get<DocumentDetail>(`/documents/${id}`)

export const uploadDocument = (file: File) => {
  const form = new FormData()
  form.append('file', file)
  return postForm<DocumentSummary>('/documents/upload', form)
}

export const importFromUrl = (url: string) =>
  post<DocumentSummary>('/documents/from-url', { url })

export const renameDocument = (id: number, title: string) =>
  patch<DocumentSummary>(`/documents/${id}`, { title })

export const deleteDocument = (id: number) => del<{ id: number }>(`/documents/${id}`)

export const saveProgress = (id: number, lastParagraphIdx: number) =>
  put<{ last_paragraph_idx: number }>(`/documents/${id}/progress`, {
    last_paragraph_idx: lastParagraphIdx
  })

export const getAnnotations = (id: number, strategy: string, wordbook: string) =>
  get<AnnotationMap>(`/documents/${id}/annotations`, { strategy, wordbook })

export const lookupWord = (word: string) =>
  get<DictEntry | null>(`/dict/${encodeURIComponent(word)}`)

export const addToVocabulary = (wordId: number) =>
  post<{ added: boolean; word: string }>('/study/vocabulary', { word_id: wordId })
