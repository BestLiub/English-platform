<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { ElMessageBox } from 'element-plus'
import StudyTabs from '@/components/StudyTabs.vue'
import WordCard from '@/components/WordCard.vue'
import { useImmersionStore } from '@/stores/immersion'
import { useSettingsStore } from '@/stores/settings'

const immersion = useImmersionStore()
const settings = useSettingsStore()

// 翻面状态只属于当前这张卡，换词时一定回到正面
const revealed = ref(false)

const progressPercent = computed(() => {
  const { mastered, total } = immersion.progress
  return total ? (mastered / total) * 100 : 0
})

/** 抽下一张卡；失败时提示由 api 拦截器负责，页面进入可重试的空状态 */
async function drawNext(): Promise<boolean> {
  try {
    await immersion.next(settings.activeWordbook)
    return true
  } catch {
    return false
  }
}

function reveal() {
  if (!immersion.word || immersion.loading || immersion.submitting) return
  revealed.value = true
}

async function skip() {
  if (!immersion.word || revealed.value || immersion.loading || immersion.submitting) return
  try {
    await immersion.skip()
  } catch {
    /* 拦截器已提示；停在当前卡片，用户可以重试 */
  }
}

/** 看过释义后只前进：不提交任何评价，抽下一张即可 */
async function advance() {
  if (!revealed.value || immersion.loading || immersion.submitting) return
  if (await drawNext()) revealed.value = false
}

async function restart() {
  if (immersion.submitting) return
  const book = immersion.currentBook || settings.activeWordbook
  try {
    await ElMessageBox.confirm(
      `将清空「${book}」词库的沉浸进度，清空后无法恢复。`,
      '重新开始',
      { confirmButtonText: '清空并重新开始', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return  // 用户取消
  }
  try {
    await immersion.restart()
    revealed.value = false
  } catch {
    /* 拦截器已提示 */
  }
}

function onKeydown(event: KeyboardEvent) {
  const target = event.target as HTMLElement | null
  if (target && ['INPUT', 'TEXTAREA', 'SELECT', 'BUTTON'].includes(target.tagName)) return
  if (immersion.finished || immersion.loading || immersion.submitting || !immersion.word) return

  // 空格只负责翻面，避免按住时连着翻过下一张
  if (event.code === 'Space') {
    event.preventDefault()
    if (!revealed.value) reveal()
    return
  }

  // 回车：没翻面先翻面，翻面后进入下一个
  if (event.key === 'Enter') {
    event.preventDefault()
    if (revealed.value) advance()
    else reveal()
    return
  }

  // 没翻面时右箭头 = 我认识（跳过）；翻面后 = 下一个
  if (event.key === 'ArrowRight') {
    event.preventDefault()
    if (revealed.value) advance()
    else skip()
  }
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
  // 在别处切换了词库：旧卡片和旧进度都不再属于当前词库，清掉后按新词库重抽
  if (immersion.currentBook && immersion.currentBook !== settings.activeWordbook) {
    immersion.resetLocalState()
  }
  // 从别的页面切回来时保留当前卡片，只有还没有词时才抽第一张
  if (!immersion.loading && !immersion.submitting && !immersion.word) void drawNext()
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
})
</script>

<template>
  <div>
    <header class="mb-8 flex items-end justify-between">
      <div>
        <div class="text-xs uppercase tracking-[0.18em] text-gray-400">Immersion</div>
        <h1 class="mt-3 font-serif text-3xl text-gray-900">沉浸模式</h1>
      </div>
      <div class="text-sm text-gray-400">
        已掌握 {{ immersion.progress.mastered }} / {{ immersion.progress.total }}
      </div>
    </header>

    <StudyTabs />

    <div class="mb-8 h-1 w-full overflow-hidden rounded-full bg-gray-100">
      <div
        class="h-full bg-gray-900 transition-all duration-300"
        :style="{ width: `${progressPercent}%` }"
      />
    </div>

    <!-- 这个词库背完了 -->
    <div v-if="immersion.finished" class="rounded-2xl border bg-white px-10 py-14 text-center">
      <h2 class="font-serif text-2xl text-gray-900">这个词库背完了</h2>
      <p class="mt-2 text-sm text-gray-400">
        已掌握 {{ immersion.progress.mastered }} / {{ immersion.progress.total }}
      </p>
      <div class="mt-10 flex justify-center gap-3">
        <el-button
          type="primary"
          :disabled="immersion.submitting || immersion.loading"
          @click="restart"
        >
          重新开始
        </el-button>
      </div>
    </div>

    <!-- 还在抽词 / 抽词失败 -->
    <div v-else-if="!immersion.word" class="rounded-2xl border bg-white px-10 py-20 text-center">
      <div v-if="immersion.loading" class="text-sm text-gray-400">正在抽词…</div>
      <template v-else>
        <p class="text-sm text-gray-900">没能抽到词</p>
        <p class="mt-2 text-xs text-gray-400">检查一下后端是否已经启动。</p>
        <el-button class="mt-6" @click="drawNext">重试</el-button>
      </template>
    </div>

    <!-- 卡片 -->
    <template v-else>
      <WordCard
        :item="immersion.word"
        :revealed="revealed"
        :show-badge="false"
        :show-rating-hint="false"
        @flip="reveal"
      />

      <div class="mt-6">
        <!-- 还没翻面：看释义，或者直接跳过 -->
        <div v-if="!revealed" class="space-y-3">
          <button
            class="w-full rounded-xl bg-gray-900 px-6 py-4 text-sm font-medium text-white transition-colors hover:bg-gray-800 disabled:cursor-not-allowed disabled:opacity-50"
            :disabled="immersion.loading"
            @click="reveal"
          >
            显示释义<span class="text-white/40">（空格）</span>
          </button>
          <button
            class="w-full rounded-xl border bg-white px-6 py-3 text-sm text-gray-600 transition-colors hover:border-gray-400 hover:text-gray-900 disabled:cursor-not-allowed disabled:opacity-50"
            :disabled="immersion.loading || immersion.submitting"
            @click="skip"
          >
            跳过，这个词我认识<span class="text-gray-300">（→）</span>
          </button>
        </div>

        <!-- 看过释义：只进入下一个，不提交任何数据 -->
        <button
          v-else
          class="w-full rounded-xl bg-gray-900 px-6 py-4 text-sm font-medium text-white transition-colors hover:bg-gray-800 disabled:cursor-not-allowed disabled:opacity-50"
          :disabled="immersion.loading"
          @click="advance"
        >
          下一个
        </button>
      </div>

      <p class="mt-6 text-center text-xs text-gray-300">
        空格翻面，右箭头跳过；跳过的词以后不再出现
      </p>
    </template>
  </div>
</template>
