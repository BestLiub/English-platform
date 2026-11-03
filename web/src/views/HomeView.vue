<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { get } from '@/api/client'
import { useStudyStore } from '@/stores/study'
import { useSettingsStore } from '@/stores/settings'

interface Wordbook {
  key: string
  name: string
  count: number
}

const study = useStudyStore()
const settings = useSettingsStore()

const wordbooks = ref<Wordbook[]>([])

const today = new Date().toLocaleDateString('zh-CN', {
  month: 'long',
  day: 'numeric',
  weekday: 'long'
})

const reviewCount = computed(() => study.plan.reviews.length)
const newCount = computed(() => study.plan.new_words.length)

/** 三个入口。副标题写清楚进去以后能做什么，而不只是四个字的标题 */
const entries = computed(() => [
  {
    to: '/study',
    kicker: 'Study',
    title: '背单词',
    subtitle: `待复习 ${reviewCount.value} · 新词 ${newCount.value}`
  },
  {
    to: '/library',
    kicker: 'Reading',
    title: '读文章',
    subtitle: '导入 PDF / EPUB / 网页，划词查义'
  },
  {
    to: '/profile',
    kicker: 'Profile',
    title: '个人',
    subtitle: '学习统计与设置'
  }
])

onMounted(async () => {
  await study.loadPlan({
    wordbook: settings.activeWordbook,
    new_limit: settings.dailyNewWords,
    reviewLimit: settings.dailyReviewLimit
  })
  try {
    wordbooks.value = await get<Wordbook[]>('/wordbooks')
  } catch {
    /* 词库没导入时首页仍然可用 */
  }
})
</script>

<template>
  <div>
    <header class="mb-10">
      <div class="text-xs uppercase tracking-[0.18em] text-gray-400">{{ today }}</div>
      <h1 class="mt-3 font-serif text-3xl text-gray-900">今天想学点什么</h1>
    </header>

    <el-alert
      v-if="study.error"
      type="warning"
      :closable="false"
      show-icon
      class="mb-8"
      title="还没读到学习计划"
    >
      <template #default>
        <div class="text-sm leading-relaxed">
          大概率是词库还没导入。在项目根目录执行
          <code class="rounded bg-gray-100 px-1.5 py-0.5 text-xs">npm run seed</code>
          导入 ECDICT 后再刷新。
        </div>
      </template>
    </el-alert>

    <div class="grid gap-4 sm:grid-cols-3">
      <router-link
        v-for="entry in entries"
        :key="entry.to"
        :to="entry.to"
        class="group flex min-h-44 flex-col justify-between rounded-xl border bg-white p-6 transition-colors hover:border-gray-400"
      >
        <div class="flex items-start justify-between">
          <span class="text-xs uppercase tracking-[0.18em] text-gray-400">{{ entry.kicker }}</span>
          <span
            aria-hidden="true"
            class="text-gray-300 transition-transform duration-200 group-hover:translate-x-0.5"
          >
            →
          </span>
        </div>

        <div class="mt-10">
          <h2 class="font-serif text-2xl text-gray-900">{{ entry.title }}</h2>
          <p class="mt-2 text-sm leading-relaxed text-gray-500">{{ entry.subtitle }}</p>
        </div>
      </router-link>
    </div>

    <div class="mt-4 flex items-center justify-between gap-4 rounded-xl border bg-white px-5 py-4">
      <div class="min-w-0">
        <div class="text-sm font-medium text-gray-900">当前词库</div>
        <div class="mt-1 text-xs text-gray-400">
          {{ wordbooks.find((w) => w.key === settings.activeWordbook)?.count?.toLocaleString() ?? '—' }} 个词
        </div>
      </div>
      <el-select v-model="settings.activeWordbook" placeholder="选择词库" class="w-40 shrink-0">
        <el-option
          v-for="item in wordbooks"
          :key="item.key"
          :label="`${item.name}（${item.count}）`"
          :value="item.key"
        />
      </el-select>
    </div>
  </div>
</template>
