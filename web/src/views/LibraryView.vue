<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  deleteDocument,
  importFromUrl,
  listDocuments,
  renameDocument,
  uploadDocument,
  type DocumentSummary
} from '@/api/documents'

const router = useRouter()

const docs = ref<DocumentSummary[]>([])
const loading = ref(false)
const busy = ref(false)
const dialogVisible = ref(false)
const tab = ref<'file' | 'url'>('file')
const url = ref('')
const fileInput = ref<HTMLInputElement | null>(null)

const TYPE_LABEL: Record<string, string> = {
  pdf: 'PDF',
  epub: 'EPUB',
  docx: 'DOCX',
  txt: 'TXT',
  md: 'MD',
  url: '网页'
}

function fmtDate(value: string) {
  const date = new Date(`${value}Z`)
  return Number.isNaN(date.getTime()) ? '' : date.toLocaleDateString('zh-CN')
}

async function refresh() {
  loading.value = true
  try {
    docs.value = await listDocuments()
  } finally {
    loading.value = false
  }
}

function pickFile() {
  fileInput.value?.click()
}

async function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return

  busy.value = true
  try {
    const doc = await uploadDocument(file)
    ElMessage.success(`已导入《${doc.title}》`)
    dialogVisible.value = false
    await refresh()
    router.push(`/read/${doc.id}`)
  } catch {
    /* 拦截器已经提示过具体原因 */
  } finally {
    busy.value = false
  }
}

async function submitUrl() {
  const value = url.value.trim()
  if (!value) return
  busy.value = true
  try {
    const doc = await importFromUrl(value)
    ElMessage.success(`已抓取《${doc.title}》`)
    url.value = ''
    dialogVisible.value = false
    await refresh()
    router.push(`/read/${doc.id}`)
  } catch {
    /* 同上 */
  } finally {
    busy.value = false
  }
}

async function rename(doc: DocumentSummary) {
  try {
    const { value } = await ElMessageBox.prompt('新的标题', '重命名', {
      inputValue: doc.title,
      confirmButtonText: '保存',
      cancelButtonText: '取消'
    })
    const title = (value ?? '').trim()
    if (!title || title === doc.title) return
    await renameDocument(doc.id, title)
    await refresh()
  } catch {
    /* 取消 */
  }
}

async function remove(doc: DocumentSummary) {
  try {
    await ElMessageBox.confirm(`删除《${doc.title}》？阅读记录也会一起删掉。`, '确认删除', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }
  await deleteDocument(doc.id)
  ElMessage.success('已删除')
  await refresh()
}

onMounted(refresh)
</script>

<template>
  <div>
    <header class="mb-10 flex items-end justify-between">
      <div>
        <div class="text-xs uppercase tracking-[0.18em] text-gray-400">Reading</div>
        <h1 class="mt-3 font-serif text-3xl text-gray-900">精读</h1>
      </div>
      <el-button type="primary" @click="dialogVisible = true">导入文章</el-button>
    </header>

    <div v-if="loading && docs.length === 0" class="rounded-xl border bg-white px-8 py-16 text-center">
      <p class="text-sm text-gray-400">正在读取文章库…</p>
    </div>

    <div
      v-else-if="docs.length === 0"
      class="rounded-xl border border-dashed bg-white px-8 py-16 text-center"
    >
      <p class="text-sm text-gray-500">还没有文章。</p>
      <p class="mt-2 text-xs text-gray-400">
        支持 txt / md / pdf / docx / epub，也可以直接粘网页链接。
      </p>
      <el-button class="mt-6" @click="dialogVisible = true">导入第一篇</el-button>
    </div>

    <ul v-else class="space-y-2">
      <li
        v-for="doc in docs"
        :key="doc.id"
        class="group flex items-center gap-4 rounded-xl border bg-white px-5 py-4 transition-colors hover:border-gray-300"
      >
        <span class="rounded-md bg-gray-100 px-2 py-1 text-[11px] text-gray-500">
          {{ TYPE_LABEL[doc.source_type] ?? doc.source_type }}
        </span>

        <button class="min-w-0 flex-1 text-left" @click="router.push(`/read/${doc.id}`)">
          <span class="block truncate text-sm text-gray-900">{{ doc.title }}</span>
          <span class="mt-1 block truncate text-xs text-gray-400">
            {{ doc.paragraph_count }} 段 · {{ doc.word_count.toLocaleString() }} 词<span class="hidden sm:inline"> · {{ fmtDate(doc.created_at) }}</span>
          </span>
        </button>

        <!-- 触屏没有 hover，操作按钮在小屏上常驻 -->
        <div
          class="flex shrink-0 items-center gap-1 transition-opacity md:opacity-0 md:group-hover:opacity-100"
        >
          <el-button text size="small" @click="rename(doc)">改名</el-button>
          <el-button text size="small" @click="remove(doc)">删除</el-button>
        </div>

        <el-button
          text
          size="small"
          class="hidden shrink-0 md:inline-flex"
          @click="router.push(`/read/${doc.id}`)"
        >
          阅读
        </el-button>
      </li>
    </ul>

    <el-dialog v-model="dialogVisible" title="导入文章" width="min(520px, 92vw)">
      <div class="mb-6 flex gap-1 rounded-lg border p-0.5">
        <button
          v-for="item in (['file', 'url'] as const)"
          :key="item"
          class="flex-1 rounded-md px-4 py-2 text-sm transition-colors"
          :class="tab === item ? 'bg-gray-900 text-white' : 'text-gray-500 hover:text-gray-900'"
          @click="tab = item"
        >
          {{ item === 'file' ? '上传文件' : '网页链接' }}
        </button>
      </div>

      <div v-if="tab === 'file'" class="rounded-xl border border-dashed px-6 py-10 text-center">
        <p class="text-sm text-gray-600">选择本地文件</p>
        <p class="mt-1 text-xs text-gray-400">txt / md / pdf / docx / epub，单个文件不超过 30 MB</p>
        <el-button class="mt-5" :loading="busy" @click="pickFile">
          {{ busy ? '正在解析…' : '选择文件' }}
        </el-button>
        <input
          ref="fileInput"
          type="file"
          accept=".txt,.md,.markdown,.pdf,.docx,.epub"
          class="hidden"
          @change="onFileChange"
        />
      </div>

      <div v-else>
        <el-input
          v-model="url"
          placeholder="https://example.com/article"
          :disabled="busy"
          @keyup.enter="submitUrl"
        />
        <p class="mt-2 text-xs text-gray-400">只抽取正文，导航和评论区会被丢掉。</p>
        <el-button class="mt-4 w-full" type="primary" :loading="busy" @click="submitUrl">
          {{ busy ? '正在抓取…' : '抓取正文' }}
        </el-button>
      </div>
    </el-dialog>
  </div>
</template>
