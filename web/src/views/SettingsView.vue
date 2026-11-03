<script setup lang="ts">
import { useSettingsStore } from '@/stores/settings'

const settings = useSettingsStore()

const strategies = [
  { value: 'beyond', label: '只标超纲词', hint: '不在当前词库里的词才加注释，日常推荐' },
  { value: 'unmastered', label: '只标没掌握的词', hint: '结合你的复习记录，已经记熟的词不标' },
  { value: 'all', label: '全部标注', hint: '每个词都显示释义，适合精读难文' }
]
</script>

<template>
  <div>
    <header class="mb-10">
      <div class="text-xs uppercase tracking-[0.18em] text-gray-400">Settings</div>
      <h1 class="mt-3 font-serif text-3xl text-gray-900">设置</h1>
    </header>

    <section class="rounded-xl border bg-white p-6">
      <h2 class="text-sm font-medium text-gray-900">每日新词量</h2>
      <p class="mt-1 text-xs text-gray-400">复习卡片永远优先，新词按这个数量补足。</p>
      <el-input-number v-model="settings.dailyNewWords" :min="5" :max="100" :step="5" class="mt-4" />
    </section>

    <section class="mt-4 rounded-xl border bg-white p-6">
      <h2 class="text-sm font-medium text-gray-900">生词注释</h2>
      <p class="mt-1 text-xs text-gray-400">阅读时在生词下方显示中文提示。注释太多会淹没原文。</p>
      <div class="mt-4 space-y-2">
        <label
          v-for="item in strategies"
          :key="item.value"
          class="flex cursor-pointer items-start gap-3 rounded-lg border px-4 py-3 transition-colors hover:bg-gray-50"
          :class="settings.annotationStrategy === item.value ? 'border-gray-900' : ''"
        >
          <input
            v-model="settings.annotationStrategy"
            type="radio"
            :value="item.value"
            class="mt-1 accent-gray-900"
          />
          <span>
            <span class="block text-sm text-gray-900">{{ item.label }}</span>
            <span class="mt-0.5 block text-xs text-gray-400">{{ item.hint }}</span>
          </span>
        </label>
      </div>
    </section>

    <section class="mt-4 rounded-xl border bg-white p-6">
      <h2 class="text-sm font-medium text-gray-900">关于数据</h2>
      <p class="mt-1 text-xs leading-relaxed text-gray-400">
        词库、学习记录、文章都保存在你自己的电脑上，不上传任何服务器。
        应用完全离线可用，不需要注册账号，也不需要配置任何密钥。
      </p>
    </section>
  </div>
</template>
