<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import ReviewChart from '@/components/ReviewChart.vue'
import { useStatsStore, type DailyPoint } from '@/stores/stats'

const router = useRouter()
const stats = useStatsStore()

const view = ref<'chart' | 'table'>('chart')

const RANGES = [
  { value: 7, label: '7 天' },
  { value: 30, label: '30 天' },
  { value: 90, label: '90 天' }
]

function isoDay(date: Date) {
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${date.getFullYear()}-${m}-${d}`
}

/** 接口只返回有复习的天，这里把空白天补齐，横轴才是连续的 */
const filled = computed<DailyPoint[]>(() => {
  const byDate = new Map((stats.data?.daily ?? []).map((d) => [d.date, d]))
  const out: DailyPoint[] = []
  const today = new Date()
  for (let i = stats.days - 1; i >= 0; i--) {
    const day = new Date(today)
    day.setDate(today.getDate() - i)
    const key = isoDay(day)
    out.push(byDate.get(key) ?? { date: key, total: 0, good: 0 })
  }
  return out
})

const hasReviews = computed(() => (stats.data?.total_reviews ?? 0) > 0)
const windowTotal = computed(() => filled.value.reduce((sum, d) => sum + d.total, 0))
const accuracy = computed(() => {
  const total = stats.data?.total_reviews ?? 0
  return total ? Math.round(((stats.data?.good_reviews ?? 0) / total) * 100) : 0
})
const tableRows = computed(() => filled.value.filter((d) => d.total > 0).slice().reverse())

onMounted(() => stats.load(30))
</script>

<template>
  <div>
    <header class="mb-10">
      <div class="text-xs uppercase tracking-[0.18em] text-gray-400">Stats</div>
      <h1 class="mt-3 font-serif text-3xl text-gray-900">学习统计</h1>
    </header>

    <div class="grid grid-cols-3 gap-4">
      <div class="rounded-xl border bg-white p-6">
        <div class="text-xs text-gray-400">累计复习</div>
        <div class="mt-2 font-serif text-3xl text-gray-900">{{ stats.data?.total_reviews ?? 0 }}</div>
      </div>
      <div class="rounded-xl border bg-white p-6">
        <div class="text-xs text-gray-400">已学单词</div>
        <div class="mt-2 font-serif text-3xl text-gray-900">{{ stats.data?.learned_words ?? 0 }}</div>
      </div>
      <div class="rounded-xl border bg-white p-6">
        <div class="text-xs text-gray-400">正确率</div>
        <div class="mt-2 font-serif text-3xl text-gray-900">
          {{ accuracy }}<span class="text-lg text-gray-400">%</span>
        </div>
      </div>
    </div>

    <div class="mt-8 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
      <div>
        <h2 class="text-sm font-medium text-gray-900">复习趋势</h2>
        <p class="mt-1 text-xs text-gray-400">按本地日期统计，凌晨背的词不会算到前一天</p>
      </div>
      <div class="flex items-center gap-3">
        <div class="flex rounded-lg border p-0.5">
          <button
            v-for="item in RANGES"
            :key="item.value"
            class="whitespace-nowrap rounded-md px-3 py-1 text-xs transition-colors"
            :class="
              stats.days === item.value
                ? 'bg-gray-900 text-white'
                : 'text-gray-500 hover:text-gray-900'
            "
            @click="stats.load(item.value)"
          >
            {{ item.label }}
          </button>
        </div>
        <div class="flex rounded-lg border p-0.5">
          <button
            v-for="mode in (['chart', 'table'] as const)"
            :key="mode"
            class="whitespace-nowrap rounded-md px-3 py-1 text-xs transition-colors"
            :class="view === mode ? 'bg-gray-900 text-white' : 'text-gray-500 hover:text-gray-900'"
            @click="view = mode"
          >
            {{ mode === 'chart' ? '图表' : '表格' }}
          </button>
        </div>
      </div>
    </div>

    <section class="mt-3 rounded-xl border bg-white px-5 pb-5 pt-4">
      <div v-if="stats.error" class="px-2 py-16 text-center text-sm text-gray-500">
        没能读到统计数据：{{ stats.error }}
      </div>

      <div v-else-if="!hasReviews" class="px-2 py-16 text-center">
        <p class="text-sm text-gray-500">还没有复习记录。</p>
        <p class="mt-2 text-xs text-gray-400">背几张卡片之后，这里就会出现每天的复习量和正确率。</p>
        <el-button class="mt-6" @click="router.push('/study')">去背单词</el-button>
      </div>

      <div v-else-if="windowTotal === 0" class="px-2 py-16 text-center">
        <p class="text-sm text-gray-500">这段时间没有复习记录。</p>
        <p class="mt-2 text-xs text-gray-400">换一个更长的时间范围看看。</p>
      </div>

      <!-- 重新拉数据时保留上一次的渲染，只降低透明度，避免闪一下骨架屏 -->
      <div v-else :class="stats.loading ? 'opacity-60' : ''">
        <ReviewChart v-if="view === 'chart'" :daily="filled" />

        <table v-else class="w-full text-sm tabular-nums">
          <thead>
            <tr class="text-xs text-gray-400">
              <th class="pb-2 text-left font-normal">日期</th>
              <th class="pb-2 text-right font-normal">复习</th>
              <th class="pb-2 text-right font-normal">记住</th>
              <th class="pb-2 text-right font-normal">正确率</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in tableRows" :key="row.date" class="border-t">
              <td class="py-2 text-gray-600">{{ row.date }}</td>
              <td class="py-2 text-right text-gray-900">{{ row.total }}</td>
              <td class="py-2 text-right text-gray-600">{{ row.good }}</td>
              <td class="py-2 text-right text-gray-600">
                {{ Math.round((row.good / row.total) * 100) }}%
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>
