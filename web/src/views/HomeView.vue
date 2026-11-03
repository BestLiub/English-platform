<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { get } from '@/api/client'
import { useStudyStore } from '@/stores/study'
import { useSettingsStore } from '@/stores/settings'

interface Wordbook {
  key: string
  name: string
  count: number
}

const router = useRouter()
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
const hasWork = computed(() => reviewCount.value + newCount.value > 0)

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

function start() {
  router.push('/study')
}
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

    <div class="grid grid-cols-2 gap-4">
      <div class="rounded-xl border bg-white p-6">
        <div class="text-xs text-gray-400">待复习</div>
        <div class="mt-2 font-serif text-4xl text-gray-900">{{ reviewCount }}</div>
      </div>
      <div class="rounded-xl border bg-white p-6">
        <div class="text-xs text-gray-400">今日新词</div>
        <div class="mt-2 font-serif text-4xl text-gray-900">{{ newCount }}</div>
      </div>
    </div>

    <div class="mt-4 flex items-center justify-between rounded-xl border bg-white p-6">
      <div>
        <div class="text-sm font-medium text-gray-900">当前词库</div>
        <div class="mt-1 text-xs text-gray-400">
          {{ wordbooks.find((w) => w.key === settings.activeWordbook)?.count?.toLocaleString() ?? '—' }} 个词
        </div>
      </div>
      <el-select v-model="settings.activeWordbook" placeholder="选择词库" class="w-40">
        <el-option
          v-for="item in wordbooks"
          :key="item.key"
          :label="`${item.name}（${item.count}）`"
          :value="item.key"
        />
      </el-select>
    </div>

    <button
      class="mt-8 flex w-full items-center justify-center rounded-xl bg-gray-900 px-6 py-4 text-sm font-medium text-white transition-colors hover:bg-gray-800 disabled:cursor-not-allowed disabled:bg-gray-300"
      :disabled="!hasWork"
      @click="start"
    >
      {{ hasWork ? '开始今天的学习' : '今天没有待办，去导入一篇文章吧' }}
    </button>
  </div>
</template>
