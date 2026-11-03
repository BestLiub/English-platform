<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const items = [
  { name: 'home', path: '/', label: '今日', icon: 'Sunrise' },
  { name: 'study', path: '/study', label: '背单词', icon: 'Collection' },
  { name: 'library', path: '/library', label: '精读', icon: 'Reading' },
  { name: 'stats', path: '/stats', label: '统计', icon: 'DataLine' },
  { name: 'settings', path: '/settings', label: '设置', icon: 'Setting' }
]

const activeName = computed(() => (route.name === 'reader' ? 'library' : (route.name as string)))
</script>

<template>
  <div class="flex h-full flex-col md:flex-row">
    <aside class="shrink-0 border-b bg-white md:flex md:w-56 md:flex-col md:border-b-0 md:border-r">
      <div class="px-5 pb-2 pt-4 md:px-6 md:pb-6 md:pt-7">
        <div class="font-serif text-xl tracking-tight text-gray-900">English</div>
        <div class="mt-1 hidden text-xs text-gray-400 md:block">背单词 · 精读 · 模考</div>
      </div>

      <nav class="flex gap-0.5 overflow-x-auto px-2 pb-2 md:flex-1 md:flex-col md:gap-1 md:overflow-visible md:px-3 md:pb-0">
        <router-link
          v-for="item in items"
          :key="item.name"
          :to="item.path"
          class="relative flex shrink-0 items-center gap-2 rounded-lg px-2.5 py-2 text-sm text-gray-600 transition-colors hover:bg-gray-50 hover:text-gray-900 md:px-3"
          :class="activeName === item.name ? 'bg-gray-50 font-medium text-gray-900' : ''"
        >
          <span
            v-if="activeName === item.name"
            class="absolute left-0 top-1/2 hidden h-4 w-0.5 -translate-y-1/2 rounded-full bg-gray-900 md:block"
          />
          <el-icon :size="16" class="hidden md:inline-flex"><component :is="item.icon" /></el-icon>
          {{ item.label }}
        </router-link>
      </nav>

      <div class="hidden border-t px-6 py-4 text-[11px] leading-relaxed text-gray-400 md:block">
        <div>v0.1.0 · 本地版</div>
        <div class="mt-1">数据保存在本机</div>
      </div>
    </aside>

    <main class="min-w-0 flex-1 overflow-y-auto">
      <div class="mx-auto max-w-4xl px-5 py-8 md:px-10 md:py-12">
        <slot />
      </div>
    </main>
  </div>
</template>
