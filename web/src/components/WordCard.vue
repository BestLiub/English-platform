<script setup lang="ts">
import type { PlanItem } from '@/stores/study'

const props = defineProps<{
  item: PlanItem | null
  revealed: boolean
}>()

const emit = defineEmits<{ flip: [] }>()

function speak(event: Event) {
  event.stopPropagation()
  if (!props.item) return
  const synth = window.speechSynthesis
  if (!synth) return
  synth.cancel()
  const utterance = new SpeechSynthesisUtterance(props.item.word)
  utterance.lang = 'en-US'
  utterance.rate = 0.9
  synth.speak(utterance)
}
</script>

<template>
  <div
    v-if="item"
    class="w-full cursor-pointer select-none [perspective:1400px]"
    @click="emit('flip')"
  >
    <div
      class="relative h-[22rem] w-full transition-transform duration-500 [transform-style:preserve-3d]"
      :class="revealed ? '[transform:rotateY(180deg)]' : ''"
    >
      <!-- 正面：只给单词 -->
      <div
        class="absolute inset-0 flex flex-col items-center justify-center rounded-2xl border bg-white px-10 [backface-visibility:hidden]"
      >
        <div class="absolute left-6 top-6">
          <span
            class="rounded-full px-2.5 py-1 text-[11px] tracking-wide"
            :class="item.is_new ? 'bg-amber-50 text-amber-700' : 'bg-gray-100 text-gray-500'"
          >
            {{ item.is_new ? '新词' : '复习' }}
          </span>
        </div>

        <div class="font-serif text-5xl tracking-tight text-gray-900 break-all text-center">
          {{ item.word }}
        </div>

        <div class="mt-4 flex items-center gap-2 text-sm text-gray-400">
          <span v-if="item.phonetic" class="font-mono">{{ item.phonetic }}</span>
          <button
            class="rounded-full p-1.5 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-900"
            title="朗读"
            @click="speak"
          >
            <el-icon :size="16"><Microphone /></el-icon>
          </button>
        </div>

        <div class="absolute bottom-6 text-xs text-gray-300">
          点击卡片或按空格查看释义
        </div>
      </div>

      <!-- 背面：释义 -->
      <div
        class="absolute inset-0 flex flex-col overflow-y-auto rounded-2xl border bg-white px-10 py-9 [backface-visibility:hidden] [transform:rotateY(180deg)]"
      >
        <div class="flex items-baseline gap-3">
          <span class="font-serif text-xl text-gray-900">{{ item.word }}</span>
          <span v-if="item.phonetic" class="font-mono text-xs text-gray-400">{{ item.phonetic }}</span>
        </div>

        <div class="mt-6 flex-1 whitespace-pre-line text-lg leading-relaxed text-gray-800">
          {{ item.translation || '这个词库里暂时没有释义' }}
        </div>

        <div class="mt-4 text-xs text-gray-300">
          1 不认识 · 2 记忆模糊
        </div>
      </div>
    </div>
  </div>
</template>
