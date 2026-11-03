<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  addToVocabulary,
  getAnnotations,
  getDocument,
  lookupWord,
  saveProgress,
  type AnnotationMap,
  type AnnotationSpan,
  type DictEntry,
  type DocumentDetail
} from '@/api/documents'
import { useSettingsStore } from '@/stores/settings'

interface Segment {
  text: string
  gloss: string | null
}

interface Popover {
  word: string
  left: number
  top: number
  placement: 'below' | 'above'
  loading: boolean
  entry: DictEntry | null
  adding: boolean
}

const route = useRoute()
const router = useRouter()
const settings = useSettingsStore()

const documentId = Number(route.params.id)

const doc = ref<DocumentDetail | null>(null)
const annotations = ref<AnnotationMap | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const popover = ref<Popover | null>(null)
const article = ref<HTMLElement | null>(null)

let scroller: HTMLElement | null = null
let saveTimer: number | undefined

const STRATEGIES = [
  { value: 'beyond', label: '超纲词' },
  { value: 'unmastered', label: '未掌握' },
  { value: 'all', label: '全部' }
] as const

const segments = computed<Record<number, Segment[]>>(() => {
  const result: Record<number, Segment[]> = {}
  const spans = annotations.value?.paragraphs ?? {}
  for (const paragraph of doc.value?.paragraphs ?? []) {
    result[paragraph.idx] = buildSegments(paragraph.text, spans[String(paragraph.idx)] ?? [])
  }
  return result
})

const annotatedCount = computed(() =>
  Object.values(annotations.value?.paragraphs ?? {}).reduce((sum, list) => sum + list.length, 0)
)

function buildSegments(text: string, spans: AnnotationSpan[]): Segment[] {
  if (spans.length === 0) return [{ text, gloss: null }]

  const out: Segment[] = []
  let cursor = 0
  for (const span of spans) {
    if (span.start > cursor) out.push({ text: text.slice(cursor, span.start), gloss: null })
    out.push({ text: text.slice(span.start, span.end), gloss: span.translation })
    cursor = span.end
  }
  if (cursor < text.length) out.push({ text: text.slice(cursor), gloss: null })
  return out
}

async function load() {
  loading.value = true
  error.value = null
  try {
    doc.value = await getDocument(documentId)
    await loadAnnotations()
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    loading.value = false
  }

  // 必须等 loading 关掉、<article> 真正渲染出来，否则拿不到段落元素
  await nextTick()
  if (doc.value) restoreProgress(doc.value.last_paragraph_idx)
}

async function loadAnnotations() {
  annotations.value = await getAnnotations(
    documentId,
    settings.annotationStrategy,
    settings.activeWordbook
  )
}

function restoreProgress(idx: number) {
  if (!idx || !article.value) return
  const target = article.value.querySelector<HTMLElement>(`[data-idx="${idx}"]`)
  target?.scrollIntoView({ block: 'start' })
}

function scheduleSave() {
  if (!scroller || !article.value) return
  window.clearTimeout(saveTimer)
  saveTimer = window.setTimeout(() => {
    const top = scroller!.getBoundingClientRect().top + 120
    let current = 0
    for (const el of article.value!.querySelectorAll<HTMLElement>('[data-idx]')) {
      if (el.getBoundingClientRect().top <= top) current = Number(el.dataset.idx)
      else break
    }
    saveProgress(documentId, current).catch(() => {
      /* 进度保存失败不打断阅读 */
    })
  }, 1000)
}

function onMouseUp() {
  const selection = window.getSelection()
  if (!selection || selection.isCollapsed) return

  const text = selection.toString().trim()
  const match = text.match(/[A-Za-z][A-Za-z'\-]*/)
  if (!match) return

  const rect = selection.getRangeAt(0).getBoundingClientRect()
  openLookup(match[0], rect)
}

async function openLookup(word: string, rect: DOMRect) {
  const width = 320
  const center = rect.left + rect.width / 2
  const left = Math.min(Math.max(center - width / 2, 12), window.innerWidth - width - 12)
  const below = rect.bottom + 8
  const placement: 'below' | 'above' = below + 220 > window.innerHeight ? 'above' : 'below'

  popover.value = {
    word,
    left,
    top: placement === 'below' ? below : rect.top - 8,
    placement,
    loading: true,
    entry: null,
    adding: false
  }

  const requestWord = word
  try {
    const entry = await lookupWord(requestWord)
    if (popover.value?.word === requestWord) {
      popover.value.entry = entry
      popover.value.loading = false
    }
  } catch {
    if (popover.value?.word === requestWord) popover.value.loading = false
  }
}

async function addWord() {
  const entry = popover.value?.entry
  if (!entry?.word_id || entry.in_user_words) return
  popover.value!.adding = true
  try {
    const result = await addToVocabulary(entry.word_id)
    entry.in_user_words = true
    ElMessage.success(result.added ? `已加入词库：${result.word}` : '这个词已经在词库里了')
  } finally {
    if (popover.value) popover.value.adding = false
  }
}

function closePopover(event: MouseEvent) {
  const target = event.target as HTMLElement | null
  if (target?.closest('[data-dict-popover]')) return
  popover.value = null
}

watch(
  () => settings.annotationStrategy,
  async () => {
    await loadAnnotations()
  }
)

onMounted(async () => {
  document.addEventListener('click', closePopover)
  await load()
  scroller = article.value?.closest('main') ?? null
  scroller?.addEventListener('scroll', scheduleSave, { passive: true })
})

onBeforeUnmount(() => {
  document.removeEventListener('click', closePopover)
  scroller?.removeEventListener('scroll', scheduleSave)
  window.clearTimeout(saveTimer)
})
</script>

<template>
  <div>
    <header class="mb-8">
      <button class="text-xs text-gray-400 hover:text-gray-900" @click="router.push('/library')">
        ← 文章库
      </button>

      <div class="mt-4 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div class="min-w-0">
          <h1 class="truncate font-serif text-2xl text-gray-900">{{ doc?.title ?? '加载中…' }}</h1>
          <p v-if="doc" class="mt-1 text-xs text-gray-400">
            {{ doc.word_count.toLocaleString() }} 词 · {{ annotatedCount }} 处提示
          </p>
        </div>

        <div class="flex shrink-0 rounded-lg border p-0.5">
          <button
            v-for="item in STRATEGIES"
            :key="item.value"
            class="whitespace-nowrap rounded-md px-3 py-1 text-xs transition-colors"
            :class="
              settings.annotationStrategy === item.value
                ? 'bg-gray-900 text-white'
                : 'text-gray-500 hover:text-gray-900'
            "
            @click="settings.annotationStrategy = item.value"
          >
            {{ item.label }}
          </button>
        </div>
      </div>
    </header>

    <div v-if="error" class="rounded-xl border bg-white px-8 py-16 text-center">
      <p class="text-sm text-gray-900">打不开这篇文章</p>
      <p class="mt-2 text-xs text-gray-400">{{ error }}</p>
      <el-button class="mt-6" @click="router.push('/library')">回到文章库</el-button>
    </div>

    <div v-else-if="loading" class="rounded-xl border bg-white px-8 py-20 text-center">
      <p class="text-sm text-gray-400">正在打开文章…</p>
    </div>

    <article
      v-else
      ref="article"
      class="mx-auto max-w-2xl space-y-5 font-serif text-[17px] leading-[1.95] text-gray-800"
      @mouseup="onMouseUp"
    >
      <p v-for="paragraph in doc?.paragraphs" :key="paragraph.idx" :data-idx="paragraph.idx">
        <template v-for="(segment, index) in segments[paragraph.idx]" :key="index">
          <ruby v-if="segment.gloss" class="annotation">
            {{ segment.text }}<rt>{{ segment.gloss }}</rt>
          </ruby>
          <template v-else>{{ segment.text }}</template>
        </template>
      </p>
    </article>

    <div
      v-if="popover"
      data-dict-popover
      class="fixed z-30 w-80 rounded-xl border bg-white p-4 shadow-lg"
      :style="{
        left: `${popover.left}px`,
        top: `${popover.top}px`,
        transform: popover.placement === 'above' ? 'translateY(-100%)' : undefined
      }"
    >
      <div v-if="popover.loading" class="py-2 text-center text-xs text-gray-400">查询中…</div>

      <template v-else-if="popover.entry">
        <div class="flex items-baseline gap-2">
          <span class="font-serif text-lg text-gray-900">{{ popover.entry.word }}</span>
          <span v-if="popover.entry.phonetic" class="font-mono text-xs text-gray-400">
            {{ popover.entry.phonetic }}
          </span>
        </div>
        <p v-if="popover.entry.lemma" class="mt-1 text-[11px] text-gray-400">
          原形：{{ popover.entry.lemma }}
        </p>
        <p class="mt-2 whitespace-pre-line text-sm leading-relaxed text-gray-700">
          {{ popover.entry.translation || '这个词库里没有中文释义' }}
        </p>

        <div class="mt-3 flex items-center justify-between">
          <span class="text-[11px] text-gray-300">
            {{ popover.entry.tag ? popover.entry.tag.replace(/ /g, ' · ') : '' }}
          </span>
          <el-button
            size="small"
            :disabled="popover.entry.in_user_words || !popover.entry.word_id"
            :loading="popover.adding"
            @click="addWord"
          >
            {{ popover.entry.in_user_words ? '已在词库' : '加入词库' }}
          </el-button>
        </div>
      </template>

      <div v-else class="py-2 text-center">
        <p class="text-sm text-gray-600">词库里没有 “{{ popover.word }}”</p>
        <p class="mt-1 text-xs text-gray-400">可能是专有名词或生造词</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.annotation {
  ruby-position: under;
}

.annotation rt {
  font-size: 11px;
  color: #b0aea7;
  font-family: 'Inter', 'PingFang SC', 'Microsoft YaHei', system-ui, sans-serif;
  text-align: center;
}
</style>
