<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import StudyTabs from '@/components/StudyTabs.vue'
import WordCard from '@/components/WordCard.vue'
import { OUTCOME_LABELS, useStudyStore, type Outcome } from '@/stores/study'
import { useSettingsStore } from '@/stores/settings'

const router = useRouter()
const study = useStudyStore()
const settings = useSettingsStore()

const outcomes: Array<'unknown' | 'vague'> = ['unknown', 'vague']
const summaryOutcomes: Outcome[] = ['skipped', 'unknown', 'vague']

const completed = computed(() => (study.started ? Math.min(study.index + 1, study.total) : 0))
const reviewCount = computed(() => study.plan.reviews.length)
const newCount = computed(() => study.plan.new_words.length)

function startNew() {
  study.startSession({
    wordbook: settings.activeWordbook,
    newLimit: settings.dailyNewWords,
    reviewLimit: settings.dailyReviewLimit
  })
}

function flip() {
  study.reveal()
}

function skip() {
  study.skip()
}

function pick(outcome: 'unknown' | 'vague') {
  study.grade(outcome)
}

function onKeydown(event: KeyboardEvent) {
  const target = event.target as HTMLElement | null
  if (target && ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName)) return
  if (study.finished || study.loading || !study.started) return

  if (event.code === 'Space' || event.key === 'Enter') {
    event.preventDefault()
    if (!study.revealed) flip()
    return
  }

  // 还没看释义时按右方向键 = 我认识，直接跳过
  if (event.key === 'ArrowRight' && !study.revealed) {
    event.preventDefault()
    skip()
    return
  }

  if (study.revealed && (event.key === '1' || event.key === '2')) {
    event.preventDefault()
    pick(event.key === '1' ? 'unknown' : 'vague')
  }
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
  // 从别的页面切回来时保留正在进行的会话，避免每次进页面都重开
  if (!study.started && !study.loading) startNew()
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
})
</script>

<template>
  <div>
    <header class="mb-8 flex items-end justify-between">
      <div>
        <div class="text-xs uppercase tracking-[0.18em] text-gray-400">Study</div>
        <h1 class="mt-3 font-serif text-3xl text-gray-900">背单词</h1>
      </div>
      <div v-if="study.started && !study.finished" class="text-sm text-gray-400">
        {{ completed }} / {{ study.total }}
      </div>
    </header>

    <StudyTabs />

    <div
      v-if="study.started && !study.finished"
      class="mb-8 h-1 w-full overflow-hidden rounded-full bg-gray-100"
    >
      <div class="h-full bg-gray-900 transition-all duration-300" :style="{ width: `${study.progress}%` }" />
    </div>

    <!-- 加载中 -->
    <div v-if="study.loading" class="rounded-2xl border bg-white px-10 py-24 text-center">
      <div class="text-sm text-gray-400">正在准备今天的卡片…</div>
    </div>

    <!-- 出错 -->
    <div v-else-if="study.error" class="rounded-2xl border bg-white px-10 py-16 text-center">
      <p class="text-sm text-gray-900">没能拿到学习计划</p>
      <p class="mt-2 text-xs text-gray-400">大概率是词库还没导入。在项目根目录执行 npm run seed。</p>
      <el-button class="mt-6" @click="startNew">重试</el-button>
    </div>

    <!-- 本次学完 -->
    <div v-else-if="study.finished" class="rounded-2xl border bg-white px-10 py-14 text-center">
      <div class="text-xs uppercase tracking-[0.18em] text-gray-400">Session complete</div>
      <h2 class="mt-4 font-serif text-2xl text-gray-900">今天的卡片都过完了</h2>
      <p class="mt-2 text-sm text-gray-400">
        复习 {{ reviewCount }} 张 · 新词 {{ newCount }} 张
      </p>

      <div class="mx-auto mt-8 flex max-w-md justify-center gap-8 text-sm">
        <div v-for="item in summaryOutcomes" :key="item" class="text-center">
          <div class="font-serif text-2xl text-gray-900">{{ study.tally[item] }}</div>
          <div class="mt-1 text-xs text-gray-400">{{ OUTCOME_LABELS[item] }}</div>
        </div>
      </div>

      <p v-if="study.tally.skipped > 0" class="mt-6 text-xs text-gray-400">
        跳过的词已标记为已掌握，以后不会再出现
      </p>

      <div class="mt-10 flex justify-center gap-3">
        <el-button @click="startNew">再来一组</el-button>
        <el-button type="primary" @click="router.push('/')">回到今日</el-button>
      </div>
    </div>

    <!-- 没卡可学 -->
    <div v-else-if="!study.started" class="rounded-2xl border border-dashed bg-white px-10 py-20 text-center">
      <p class="text-sm text-gray-500">今天没有待办的卡片。</p>
      <p class="mt-2 text-xs text-gray-400">
        到期复习已经清空，新词也背完了。去读一篇文章，或者明天再来。
      </p>
      <el-button class="mt-6" @click="router.push('/')">回到今日</el-button>
    </div>

    <!-- 卡片 -->
    <template v-else>
      <WordCard :item="study.current" :revealed="study.revealed" @flip="flip" />

      <div class="mt-6">
        <!-- 还没看释义：要么看，要么我认识直接跳过 -->
        <div v-if="!study.revealed" class="space-y-3">
          <button
            class="w-full rounded-xl bg-gray-900 px-6 py-4 text-sm font-medium text-white transition-colors hover:bg-gray-800"
            @click="flip"
          >
            显示释义　<span class="text-white/40">空格</span>
          </button>
          <button
            class="w-full rounded-xl border bg-white px-6 py-3 text-sm text-gray-600 transition-colors hover:border-gray-400 hover:text-gray-900 disabled:cursor-not-allowed disabled:opacity-50"
            :disabled="study.submitting"
            @click="skip"
          >
            下一个，这个词我认识　<span class="text-gray-300">→</span>
          </button>
        </div>

        <!-- 看过释义：这个词要复习 -->
        <div v-else class="grid grid-cols-2 gap-3">
          <button
            v-for="(outcome, i) in outcomes"
            :key="outcome"
            class="rounded-xl border bg-white px-4 py-4 text-center transition-colors hover:border-gray-400 disabled:cursor-not-allowed disabled:opacity-50"
            :disabled="study.submitting"
            @click="pick(outcome)"
          >
            <div class="text-sm text-gray-900">{{ OUTCOME_LABELS[outcome] }}</div>
            <div class="mt-1 text-[11px] text-gray-300">{{ i + 1 }}</div>
          </button>
        </div>
      </div>

      <p class="mt-6 text-center text-xs text-gray-300">
        看过释义的词会进入复习队列；直接跳过的词以后不再出现
      </p>
    </template>
  </div>
</template>
